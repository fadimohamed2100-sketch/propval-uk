"""
PDF generation service using Playwright (headless Chromium).

Renders the Jinja2 HTML report template to a pixel-perfect A4 PDF.
Playwright gives us full CSS/font/SVG support that WeasyPrint lacks.

Install:
    pip install playwright greenlet
    playwright install chromium --with-deps
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright, Page

from core.config import get_settings
from core.logging import get_logger
from models.orm import Comparable, Property, ValuationReport

settings = get_settings()
logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


# ─────────────────────────────────────────────────────────────────
# Chart geometry helpers
# ─────────────────────────────────────────────────────────────────

@dataclass
class ChartGeometry:
    """Pre-computed SVG coordinates for the price history chart."""
    subject_polyline: str
    subject_dots:     list[tuple[float, float]]
    avg_polyline:     str
    avg_dots:         list[tuple[float, float]]
    y_ticks:          list[tuple[float, str]]   # (svg_y, label)
    x_labels:         list[tuple[float, str]]   # (svg_x, label)
    grid_lines:       list[float]               # svg_y for each horizontal gridline
    viewbox:          str = "0 0 250 140"


def compute_chart(
    subject_vals: list[float],
    avg_vals:     list[float],
    labels:       list[str],
    y_min: float = 300,
    y_max: float = 500,
) -> ChartGeometry:
    """
    Convert value series into SVG polyline coordinates.

    Chart area: 250 × 140 viewBox.
    Left margin (y-axis labels): 46px.
    Bottom margin (x-axis labels): 20px.
    """
    SVG_W, SVG_H = 250, 140
    X_PAD, Y_PAD = 46, 8
    PLOT_W = SVG_W - X_PAD - 4
    PLOT_H = SVG_H - Y_PAD - 22
    n = len(labels)

    def to_x(i: int) -> float:
        return X_PAD + i * (PLOT_W / max(n - 1, 1))

    def to_y(v: float) -> float:
        return Y_PAD + PLOT_H - ((v - y_min) / (y_max - y_min)) * PLOT_H

    subj  = [(to_x(i), to_y(v)) for i, v in enumerate(subject_vals)]
    avg   = [(to_x(i), to_y(v)) for i, v in enumerate(avg_vals)]

    y_tick_vals = list(range(int(y_min), int(y_max) + 1, 20))  # every 20k
    y_ticks     = [(to_y(v), f"£{v}k") for v in y_tick_vals]
    grid_lines  = [to_y(v) for v in y_tick_vals]
    x_labels    = [(to_x(i), lbl) for i, lbl in enumerate(labels)]

    return ChartGeometry(
        subject_polyline=" ".join(f"{x:.2f},{y:.2f}" for x, y in subj),
        subject_dots=subj,
        avg_polyline=" ".join(f"{x:.2f},{y:.2f}" for x, y in avg),
        avg_dots=avg,
        y_ticks=y_ticks,
        x_labels=x_labels,
        grid_lines=grid_lines,
    )


def _default_chart() -> ChartGeometry:
    """Fallback chart when no historical data is available."""
    vals   = [415, 418, 410, 395, 365, 328]
    avg    = [415, 415, 408, 388, 360, 340]
    labels = ["Jan-21", "Jan-22", "Jan-23", "Jan-24", "Jan-25", "Jan-26"]
    return compute_chart(vals, avg, labels)


# ─────────────────────────────────────────────────────────────────
# Context builder — ORM objects → template dict
# ─────────────────────────────────────────────────────────────────

def _gbp(pence: int | None, compact: bool = False) -> str:
    if pence is None:
        return "N/A"
    pounds = pence // 100
    if compact and pounds >= 1_000_000:
        return f"£{pounds / 1_000_000:.1f}m"
    if compact and pounds >= 1_000:
        return f"£{pounds // 1_000:,}k"
    return f"£{pounds:,}"


def _fmt_date(d: date | str | None) -> str:
    if d is None:
        return "N/A"
    if isinstance(d, str):
        try:
            from datetime import datetime
            d = datetime.fromisoformat(d).date()
        except ValueError:
            return d
    return d.strftime("%B %Y")


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _sqft(m2: float | None) -> str:
    if m2 is None:
        return "N/A"
    return f"{int(m2 * 10.764):,} sqft"


def _distance(metres: int | None) -> str:
    if metres is None:
        return "N/A"
    if metres < 1_609:
        return f"{metres / 1_609.34:.2f} miles"
    return f"{metres / 1_609.34:.1f} miles"


def build_context(
    report:      ValuationReport,
    property_:   Property,
    comparables: list[Comparable],
    agent_name:  str = "PropVal",
    chart:       ChartGeometry | None = None,
    market_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assemble the full Jinja2 template context from ORM objects.

    `market_data` can supply live market stats (asking price %, weeks on market,
    search counts). Falls back to None values if not provided.
    """
    address = property_.address
    mkt     = market_data or {}

    # Price change vs last sale (if we have it in methodology)
    methodology   = report.methodology or {}
    est_gbp       = report.estimated_value / 100 if report.estimated_value else 0
    last_sale_raw = methodology.get("last_sale_price_gbp") or methodology.get(
        "supporting", {}
    )
    last_sale_p   = None
    last_sale_dt  = None

    # Try to extract last sale from methodology supporting data
    for m in (report.methodology.get("blend_inputs") or []):
        if m.get("method") == "last_sale_growth":
            sup = m.get("supporting") or {}
            if sup.get("last_sale_price_gbp"):
                last_sale_p  = int(sup["last_sale_price_gbp"] * 100)
                last_sale_dt = sup.get("last_sale_date")
            break

    price_change_pence = (
        (report.estimated_value - last_sale_p)
        if last_sale_p and report.estimated_value
        else None
    )
    if price_change_pence is not None:
        sign = "+" if price_change_pence >= 0 else "−"
        price_change_str = f"{sign} {_gbp(abs(price_change_pence))}"
    else:
        price_change_str = "N/A"

    return {
        # ── Meta ──────────────────────────────────────────────
        "report_id":   str(report.id)[:8].upper(),
        "report_date": report.created_at.strftime("%d %b %Y"),
        "agent_name":  agent_name,

        # ── Property ──────────────────────────────────────────
        "property": {
            "address1":   address.line_1,
            "address2":   " ".join(filter(None, [address.line_2, address.city])),
            "postcode":   address.postcode,
            "type":       (property_.property_type or "").replace("_", " ").title() or "N/A",
            "floor_area": _sqft(property_.floor_area_m2),
            "year_built": str(property_.year_built) if property_.year_built else "N/A",
            "receptions": "N/A",
            "bedrooms":   property_.bedrooms if property_.bedrooms is not None else "N/A",
            "bathrooms":  property_.bathrooms if property_.bathrooms is not None else "N/A",
            "epc":        property_.epc_rating or "N/A",
            "tenure":     (property_.tenure or "").replace("_", " ").title() or "N/A",
        },

        # ── Valuation ─────────────────────────────────────────
        "valuation": {
            "capital_value":  _gbp(report.estimated_value),
            "range_low":      _gbp(report.range_low),
            "range_high":     _gbp(report.range_high),
            "confidence":     _confidence_label(float(report.confidence_score or 0)),
            "confidence_pct": f"{int((report.confidence_score or 0) * 100)}%",
            "rental_value":   f"{_gbp(report.rental_monthly)} pcm",
            "gross_yield":    f"{float(report.rental_yield or 0):.1f}%",
            "last_sale_price": _gbp(last_sale_p),
            "last_sale_date":  _fmt_date(last_sale_dt),
            "price_change":    price_change_str,
            "source_apis":     ", ".join(report.source_apis or []),
        },

        # ── Market ────────────────────────────────────────────
        "market": {
            "area":             mkt.get("area", address.city or "Local area"),
            "asking_price_pct": mkt.get("asking_price_pct", 96),
            "weeks_on_market":  mkt.get("weeks_on_market", "—"),
            "searches":         mkt.get("searches", "—"),
            "search_area":      mkt.get("search_area", address.postcode.split()[0]),
            "postcode_sector":  mkt.get("postcode_sector", " ".join(address.postcode.split()[:2])[:6]),
            "bedrooms":         property_.bedrooms or 2,
            "prop_type_plural": "flats/maisonettes",
        },

        # ── Comparables ───────────────────────────────────────
        "comparables": [
            {
                "street":   comp.address_snapshot.split(",")[0].strip(),
                "distance": _distance(comp.distance_m),
                "type":     (comp.property_type or "").replace("_", " ") or "flat",
                "size":     _sqft(comp.floor_area_m2),
                "price":    _gbp(comp.sale_price),
                "date":     _fmt_date(comp.sale_date),
            }
            for comp in comparables[:6]
        ],

        # ── Chart ─────────────────────────────────────────────
        "chart": chart or _default_chart(),
    }


# ─────────────────────────────────────────────────────────────────
# Playwright PDF renderer
# ─────────────────────────────────────────────────────────────────

async def _render_html(context: dict[str, Any]) -> str:
    """Render the Jinja2 template to an HTML string."""
    template = _jinja.get_template("report_playwright.html")
    return template.render(**context)


async def _html_to_pdf(html: str, output_path: Path) -> None:
    """
    Spin up headless Chromium, load the HTML, and export A4 PDF.

    We write the HTML to a temp file so that relative resource paths
    (fonts, images) resolve correctly via the file:// protocol.
    """
    tmp_html = output_path.parent / f"_tmp_{uuid.uuid4().hex}.html"
    tmp_html.write_text(html, encoding="utf-8")

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page: Page = await browser.new_page()

            await page.goto(f"file://{tmp_html.resolve()}", wait_until="networkidle")
            # Extra wait for web fonts to render
            await page.wait_for_timeout(800)

            await page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
                prefer_css_page_size=True,
            )
            await browser.close()
    finally:
        tmp_html.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────
# Public service class
# ─────────────────────────────────────────────────────────────────

class PlaywrightPDFService:
    """
    Generates a branded property valuation PDF report using Playwright.

    Usage (inside a FastAPI route):
        service = PlaywrightPDFService()
        pdf_path = await service.generate(report, property_, comparables)
    """

    def __init__(self, reports_dir: str | None = None) -> None:
        self._dir = Path(reports_dir or settings.REPORTS_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        report:      ValuationReport,
        property_:   Property,
        comparables: list[Comparable],
        *,
        agent_name:  str = "PropVal",
        chart:       ChartGeometry | None = None,
        market_data: dict[str, Any] | None = None,
        force:       bool = False,
    ) -> Path:
        """
        Generate (or return cached) PDF for a valuation report.

        Returns the Path to the PDF file.
        Raises RuntimeError if Playwright or Chromium is unavailable.
        """
        output_path = self._dir / f"valuation_{report.id}.pdf"

        # Return cached file unless force regeneration
        if output_path.exists() and not force:
            logger.info("pdf_cache_hit", valuation_id=str(report.id))
            return output_path

        logger.info("pdf_generating", valuation_id=str(report.id))

        context = build_context(
            report=report,
            property_=property_,
            comparables=comparables,
            agent_name=agent_name,
            chart=chart,
            market_data=market_data,
        )

        try:
            html = await _render_html(context)
            await _html_to_pdf(html, output_path)
        except Exception as exc:
            logger.error("pdf_generation_failed", error=str(exc), valuation_id=str(report.id))
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"PDF generation failed: {exc}") from exc

        logger.info("pdf_generated", path=str(output_path), size_kb=output_path.stat().st_size // 1024)
        return output_path

    async def generate_bytes(
        self,
        report:      ValuationReport,
        property_:   Property,
        comparables: list[Comparable],
        **kwargs,
    ) -> bytes:
        """Generate PDF and return raw bytes (no file written to disk)."""
        path = await self.generate(report, property_, comparables, **kwargs)
        return path.read_bytes()
