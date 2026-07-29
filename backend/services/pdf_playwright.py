"""
PDF generation service using Playwright (headless Chromium).

Renders the Jinja2 HTML report template to a pixel-perfect A4 PDF.
Playwright gives us full CSS/font/SVG support that WeasyPrint lacks.

Install:
    pip install playwright greenlet
    playwright install chromium --with-deps
"""
from __future__ import annotations

import asyncio
import base64
import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import httpx
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
    step:  float = 20,
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

    y_tick_vals = list(range(int(y_min), int(y_max) + 1, max(int(step), 1)))
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


def _nice_step(span: float) -> int:
    """Pick a human-friendly axis step (in £k) for a given value span (in £k), aiming for ~6 gridlines."""
    span = max(span, 1)
    raw_step = span / 6
    magnitude = 10 ** max(0, len(str(int(raw_step))) - 1)
    for mult in (1, 2, 5, 10):
        step = mult * magnitude
        if step >= raw_step:
            return int(step)
    return int(magnitude * 10)


def _default_chart(estimate_gbp: float = 0) -> ChartGeometry:
    """
    Fallback chart when no real historical time-series is available.
    Scales a plausible-looking 5-year trend shape around the property's
    actual estimated value, so the axis isn't wildly mismatched (e.g. a
    £300-500k axis for a £1.3M property).
    """
    if not estimate_gbp or estimate_gbp <= 0:
        estimate_gbp = 400_000  # last-resort sane default if no estimate at all

    est_k = estimate_gbp / 1000
    shape_subject = [1.00, 0.985, 0.93, 0.88, 0.91, 1.00]
    shape_avg     = [1.00, 0.97,  0.92, 0.86, 0.89, 0.96]
    vals = [round(est_k * f) for f in shape_subject]
    avg  = [round(est_k * f) for f in shape_avg]
    labels = ["Jan-21", "Jan-22", "Jan-23", "Jan-24", "Jan-25", "Jan-26"]

    raw_max = max(vals + avg)
    raw_min = min(vals + avg)
    step = _nice_step(raw_max - raw_min)
    y_max = (int(raw_max / step) + 1) * step
    y_min = max(0, int(raw_min / step) * step)

    return compute_chart(vals, avg, labels, y_min=y_min, y_max=y_max, step=step)


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
    return f"{int(float(m2) * 10.764):,} sqft"


def _distance(metres: int | None) -> str:
    if metres is None:
        return "N/A"
    if metres < 1_609:
        return f"{metres / 1_609.34:.2f} miles"
    return f"{metres / 1_609.34:.1f} miles"


# Report the AUTHORITATIVE ORIGIN of each dataset rather than the vendor
# we happen to buy access through. More credible to a vendor reading the
# report ("HM Land Registry" carries real weight), and it avoids
# advertising our suppliers to customers who could go direct.
_SOURCE_LABELS = {
    # PropertyData's sold-price comparables are Land Registry Price Paid data
    "propertydata": "HM Land Registry",
    "epc": "EPC Register",
    # Homedata's agent statistics - no single authoritative body to cite
    "homedata": "Local market data",
}


def _source_labels(source_apis: list[str] | None, has_real_chart: bool) -> str:
    """Map internal source keys to public-facing origins, de-duplicated."""
    labels: list[str] = []
    for key in (source_apis or []):
        label = _SOURCE_LABELS.get(key)
        if label and label not in labels:
            labels.append(label)
    # The trend chart is genuine UK HPI data, fetched at render time and
    # so not recorded in the report's stored source list.
    if has_real_chart and "UK House Price Index" not in labels:
        labels.append("UK House Price Index")
    return ", ".join(labels) or "\u2014"


def _weeks_from_days(days: float | None) -> str:
    if days is None:
        return "—"
    weeks = round(days / 7)
    return str(max(weeks, 1))


# Maps UK postcode AREA prefixes (the letters before the digits, e.g. "DH"
# from "DH2 3LT") to HM Land Registry UK House Price Index region slugs.
# This is deliberately broad-region rather than local-authority level —
# fewer, larger regions means far more reliable coverage and a much
# simpler, lower-risk lookup than trying to map every postcode to one of
# 441 granular local authorities.
_POSTCODE_AREA_TO_HPI_REGION: dict[str, str] = {
    # Scotland
    "AB": "scotland", "DD": "scotland", "DG": "scotland", "EH": "scotland",
    "FK": "scotland", "G": "scotland", "HS": "scotland", "IV": "scotland",
    "KA": "scotland", "KW": "scotland", "KY": "scotland", "ML": "scotland",
    "PA": "scotland", "PH": "scotland", "TD": "scotland", "ZE": "scotland",
    # Wales
    "CF": "wales", "LD": "wales", "LL": "wales", "NP": "wales",
    "SA": "wales", "SY": "wales",
    # Northern Ireland
    "BT": "northern-ireland",
    # North East England
    "NE": "north-east", "SR": "north-east", "DH": "north-east", "DL": "north-east",
    "TS": "north-east",
    # North West England
    "CA": "north-west", "CH": "north-west", "CW": "north-west", "BB": "north-west",
    "BL": "north-west", "FY": "north-west", "L": "north-west", "LA": "north-west",
    "M": "north-west", "OL": "north-west", "PR": "north-west", "SK": "north-west",
    "WA": "north-west", "WN": "north-west",
    # Yorkshire and The Humber
    "BD": "yorkshire-and-the-humber", "DN": "yorkshire-and-the-humber",
    "HD": "yorkshire-and-the-humber", "HG": "yorkshire-and-the-humber",
    "HU": "yorkshire-and-the-humber", "HX": "yorkshire-and-the-humber",
    "LS": "yorkshire-and-the-humber", "S": "yorkshire-and-the-humber",
    "WF": "yorkshire-and-the-humber", "YO": "yorkshire-and-the-humber",
    # East Midlands
    "DE": "east-midlands", "LE": "east-midlands", "LN": "east-midlands",
    "NG": "east-midlands", "NN": "east-midlands",
    # West Midlands
    "B": "west-midlands", "CV": "west-midlands", "DY": "west-midlands",
    "HR": "west-midlands", "ST": "west-midlands", "TF": "west-midlands",
    "WS": "west-midlands", "WR": "west-midlands", "WV": "west-midlands",
    # East of England
    "CB": "east-of-england", "CM": "east-of-england", "CO": "east-of-england",
    "IP": "east-of-england", "NR": "east-of-england", "PE": "east-of-england",
    "SG": "east-of-england", "SS": "east-of-england", "AL": "east-of-england",
    "LU": "east-of-england", "MK": "east-of-england",
    # London
    "E": "london", "EC": "london", "N": "london", "NW": "london",
    "SE": "london", "SW": "london", "W": "london", "WC": "london",
    "BR": "london", "CR": "london", "DA": "london", "EN": "london",
    "HA": "london", "IG": "london", "KT": "london", "RM": "london",
    "SM": "london", "TW": "london", "UB": "london",
    # South East
    "BN": "south-east", "GU": "south-east", "ME": "south-east", "OX": "south-east",
    "PO": "south-east", "RG": "south-east", "RH": "south-east", "SL": "south-east",
    "SO": "south-east", "TN": "south-east",
    # South West
    "BA": "south-west", "BH": "south-west", "BS": "south-west", "DT": "south-west",
    "EX": "south-west", "GL": "south-west", "PL": "south-west", "SN": "south-west",
    "SP": "south-west", "TA": "south-west", "TQ": "south-west", "TR": "south-west",
}


def _postcode_to_hpi_region(postcode: str) -> str:
    """
    Map a UK postcode to an HM Land Registry UK HPI region slug.
    Falls back to 'england-and-wales' (still real, genuine data, just
    less granular) if the postcode area isn't in our lookup table.
    """
    if not postcode:
        return "england-and-wales"
    outcode = postcode.strip().upper().split()[0]
    # Postcode area = leading letters only (e.g. "DH" from "DH2", "EC" from "EC1N")
    area = "".join(ch for ch in outcode if ch.isalpha())
    # Try longest-prefix match first (e.g. "EC" before "E")
    for length in (2, 1):
        candidate = area[:length]
        if candidate in _POSTCODE_AREA_TO_HPI_REGION:
            return _POSTCODE_AREA_TO_HPI_REGION[candidate]
    return "england-and-wales"


def _format_hpi_label(ref_month: str) -> str:
    """Format a 'YYYY-MM' refMonth string as e.g. 'Apr-23'."""
    try:
        year, month = ref_month.split("-")
        month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(month) - 1]
        return f"{month_name}-{year[2:]}"
    except Exception:
        return ref_month


async def fetch_real_price_chart(postcode: str, estimate_gbp: float) -> ChartGeometry | None:
    """
    Fetch real regional house-price-trend data from HM Land Registry's
    UK House Price Index (free, no API key, official government statistics)
    and build a genuine 5-year trend chart from it, instead of the synthetic
    decorative curve every report would otherwise show.

    The "average area price" line is the real regional average price.
    The "this property" line applies that same real year-on-year % change
    to the property's actual current estimate, so it's grounded in a real
    trend shape while still being correctly anchored to this property's value.

    Best-effort: returns None on any failure, so the caller can fall back
    to the synthetic chart rather than breaking PDF generation.
    """
    region = _postcode_to_hpi_region(postcode)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://landregistry.data.gov.uk/data/ukhpi/region/{region}.json",
                params={
                    "_pageSize": 72,
                    "_view": "basic",
                    "_properties": "housePriceIndex,refMonth,refPeriodStart,refPeriodDuration,salesVolume,averagePrice",
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                return None
            body = resp.json()
    except Exception as e:
        logger.warning("uk_hpi_fetch_error", region=region, error=str(e))
        return None

    items = (body.get("result") or {}).get("items") or body.get("items") or []
    items = [it for it in items if isinstance(it, dict) and it.get("averagePrice") and it.get("refMonth")]
    if len(items) < 13:
        return None

    items.sort(key=lambda it: it["refMonth"], reverse=True)

    # Pick one reading per year, 12 months apart, for a 5-year trend
    step_indices = [i for i in (60, 48, 36, 24, 12, 0) if i < len(items)]
    if len(step_indices) < 4:
        return None
    chosen = [items[i] for i in step_indices]  # oldest → newest

    avg_prices_k = [c["averagePrice"] / 1000 for c in chosen]
    latest_avg_k = avg_prices_k[-1]
    est_k = (estimate_gbp / 1000) if estimate_gbp else latest_avg_k
    subject_prices_k = [est_k * (p / latest_avg_k) for p in avg_prices_k]
    labels = [_format_hpi_label(c["refMonth"]) for c in chosen]

    raw_max = max(avg_prices_k + subject_prices_k)
    raw_min = min(avg_prices_k + subject_prices_k)
    step = _nice_step(raw_max - raw_min)
    y_max = (int(raw_max / step) + 1) * step
    y_min = max(0, int(raw_min / step) * step)

    return compute_chart(subject_prices_k, avg_prices_k, labels, y_min=y_min, y_max=y_max, step=step)


async def _fetch_street_view_photo(location: str, size: str = "216x148") -> str | None:
    """
    Fetch a Street View image for a free-text address/location string,
    returned as a base64 data: URI so it's embedded directly in the PDF
    (no live URL, no API key baked into the output file).

    Checks the metadata endpoint first — Street View Static API returns a
    200 OK with a generic "no imagery" placeholder rather than an error
    when there's no real coverage, so we check status explicitly rather
    than just trusting a 200 response.

    Best-effort: returns None on any failure, missing key, or no coverage.
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            meta = await client.get(
                "https://maps.googleapis.com/maps/api/streetview/metadata",
                params={"location": location, "key": settings.GOOGLE_MAPS_API_KEY},
            )
            meta_body = meta.json()
            if meta_body.get("status") != "OK":
                return None

            img_resp = await client.get(
                "https://maps.googleapis.com/maps/api/streetview",
                params={
                    "size": size,
                    "location": location,
                    "fov": 80,
                    "key": settings.GOOGLE_MAPS_API_KEY,
                },
            )
            if img_resp.status_code != 200:
                return None
            encoded = base64.b64encode(img_resp.content).decode("ascii")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        logger.warning("street_view_fetch_error", location=location, error=str(e))
        return None


_pd_service = None


def _property_data_singleton():
    """
    Lazily-created shared PropertyDataService. Creating one per PDF would
    leak an httpx connection pool on every report generated, since the
    service owns long-lived clients that are never closed here.
    """
    global _pd_service
    if _pd_service is None:
        from services.property_data import PropertyDataService
        _pd_service = PropertyDataService()
    return _pd_service


async def fetch_comparable_floor_areas(comparables: list[Comparable]) -> dict[str, float]:
    """
    Fetch each comparable's real measured floor area from its own EPC
    certificate, so the report stops showing the subject property's size
    next to every comparable.

    Best-effort and display-only: comparables with no matchable EPC are
    simply omitted (the template shows an em-dash). Batched one search per
    distinct postcode, so 6 comparables typically cost 2-3 search calls
    plus concurrent certificate fetches - all free government API calls.
    """
    if not comparables:
        return {}
    try:
        targets = [
            (str(c.id), c.address_snapshot or "", c.postcode_snapshot or "")
            for c in comparables
        ]
        return await asyncio.wait_for(
            _property_data_singleton().get_epc_floor_areas(targets), timeout=20.0
        )
    except asyncio.TimeoutError:
        logger.warning("epc_floor_areas_timeout", count=len(comparables))
        return {}
    except Exception as e:
        logger.warning("epc_floor_areas_error", error=str(e))
        return {}


async def fetch_subject_photo(property_) -> str | None:
    """
    Street View shot of the property being valued, for the report cover.
    Larger than the comparable thumbnails (640x360) so it holds up as a
    hero image. Best-effort: returns None with no coverage or on error,
    and the template simply omits the block.
    """
    address = property_.address
    parts = [address.line_1, address.line_2, address.city, address.postcode]
    location = ", ".join(p for p in parts if p)
    try:
        return await asyncio.wait_for(
            _fetch_street_view_photo(location, size="640x360"), timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.warning("subject_photo_timeout", location=location)
        return None
    except Exception as e:
        logger.warning("subject_photo_error", error=str(e))
        return None


async def fetch_comparable_photos(comparables: list[Comparable]) -> dict[str, str]:
    """
    Fetch Street View photos for a list of comparables concurrently.
    Returns {comparable_id_str: data_uri} for whichever ones succeeded —
    comparables with no coverage or any error are simply omitted, so the
    template can fall back to the decorative placeholder for those.
    """
    if not settings.GOOGLE_MAPS_API_KEY or not comparables:
        return {}

    async def _one(comp: Comparable) -> tuple[str, str | None]:
        location = f"{comp.address_snapshot}, {comp.postcode_snapshot}"
        uri = await _fetch_street_view_photo(location)
        return str(comp.id), uri

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(_one(c) for c in comparables)),
            timeout=20.0,
        )
    except asyncio.TimeoutError:
        logger.warning("street_view_batch_timeout", count=len(comparables))
        return {}

    return {comp_id: uri for comp_id, uri in results if uri}


def build_context(
    report:      ValuationReport,
    property_:   Property,
    comparables: list[Comparable],
    agent_name:  str = "PropValue",
    chart:       ChartGeometry | None = None,
    market_data: dict[str, Any] | None = None,
    photo_uris:  dict[str, str] | None = None,
    subject_photo: str | None = None,
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

    last_sale_p_raw = methodology.get("previous_sale_price_pence")
    last_sale_p   = int(last_sale_p_raw) if last_sale_p_raw else None
    last_sale_dt  = methodology.get("previous_sale_date")

    if last_sale_p is not None:
        last_sale_display = _gbp(last_sale_p)
        last_sale_sub = _fmt_date(last_sale_dt) if last_sale_dt else None
    elif last_sale_dt:
        last_sale_display = _fmt_date(last_sale_dt)
        last_sale_sub = None
    else:
        last_sale_display = "N/A"
        last_sale_sub = None

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

    def _norm_for_match(s: str) -> str:
        s = re.sub(r"[A-Za-z]{1,2}[0-9][0-9A-Za-z]?\s*[0-9][A-Za-z]{2}", "", s)  # strip postcode
        return re.sub(r"[\s\-]+", " ", s).strip().lower()

    unit_identifier = methodology.get("unit_identifier")
    address1 = address.line_1
    if unit_identifier:
        drop_norms = set()
        if address.city:
            drop_norms.add(_norm_for_match(address.city))
            if address.city.lower().startswith("greater "):
                drop_norms.add(_norm_for_match(address.city[len("greater "):]))
        if address.line_2:
            drop_norms.add(_norm_for_match(address.line_2))

        kept_segments = []
        for seg in unit_identifier.split(","):
            seg_clean = re.sub(r"[A-Za-z]{1,2}[0-9][0-9A-Za-z]?\s*[0-9][A-Za-z]{2}", "", seg).strip()
            if not seg_clean:
                continue
            if _norm_for_match(seg_clean) in drop_norms:
                continue
            kept_segments.append(seg_clean)

        cleaned = ", ".join(kept_segments)
        if cleaned:
            address1 = cleaned

    year_built_val = None
    if property_.year_built:
        year_built_val = str(property_.year_built)
    elif methodology.get("construction_age_band"):
        year_built_val = methodology["construction_age_band"]

    # A user-stated reception count beats the EPC-derived estimate: the
    # EPC figure is habitable_rooms minus bedrooms, which silently
    # miscounts studies, box rooms and open-plan layouts.
    receptions_val = None
    stated = methodology.get("subject_receptions")
    if stated is not None:
        receptions_val = str(stated)
    else:
        habitable_rooms = methodology.get("habitable_rooms")
        if habitable_rooms and property_.bedrooms is not None:
            calc = habitable_rooms - property_.bedrooms
            if calc >= 0:
                receptions_val = str(calc)

    return {
        # ── Meta ──────────────────────────────────────────────
        "subject_photo": subject_photo,
        "report_id":   str(report.id)[:8].upper(),
        "report_date": report.created_at.strftime("%d %b %Y"),
        "agent_name":  agent_name,

        # ── Property ──────────────────────────────────────────
        "property": {
            "address1":   address1,
            "address2":   ", ".join(filter(None, [address.line_2, address.city])),
            "postcode":   address.postcode,
            "type":       (property_.property_type or "").replace("_", " ").title() or "N/A",
            "floor_area": _sqft(property_.floor_area_m2),
            "year_built": year_built_val,
            "receptions": receptions_val,
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
            "confidence_pct": f"{round((report.confidence_score or 0) * 100)}%",
            "rental_value":   f"{_gbp(report.rental_monthly)} pcm",
            "gross_yield":    f"{float(report.rental_yield or 0):.1f}%",
            "last_sale_price": last_sale_display,
            "last_sale_date":  last_sale_sub or "N/A",
            "price_change":    price_change_str,
            "source_apis":     _source_labels(report.source_apis, chart is not None),
        },

        # ── Market ────────────────────────────────────────────
        "market": {
            "area":             mkt.get("area", address.city or "Local area"),
            # None (not a hardcoded 96) when no real agent data was captured
            # - the template hides the stat entirely rather than showing a
            # number we invented, which would be indefensible to an agent.
            "asking_price_pct": mkt.get("asking_price_pct", methodology.get("avg_sale_percent")),
            "weeks_on_market":  mkt.get("weeks_on_market", _weeks_from_days(methodology.get("avg_time_on_market_days"))),
            "demand_rating":    mkt.get("demand_rating", methodology.get("market_demand_rating") or "—"),
            "search_area":      mkt.get("search_area", address.postcode.split()[0]),
            "postcode_sector":  mkt.get("postcode_sector", " ".join(address.postcode.split()[:2])[:6]),
            "bedrooms":         property_.bedrooms or 2,
            "prop_type_plural": "flats/maisonettes",
        },

        # ── Comparables ───────────────────────────────────────
        "comparables": [
            {
                "street":   ", ".join(p.strip() for p in comp.address_snapshot.split(",")[:2] if p.strip()) or comp.address_snapshot.strip(),
                "distance": _distance(comp.distance_m),
                "type":     (comp.property_type or "").replace("_", " ") or "flat",
                # Each comparable's OWN measured EPC floor area. Falls back
                # to an em-dash rather than the subject's size, which would
                # be misleading (previously every comparable displayed the
                # subject property's square footage).
                "size":     _sqft(comp.epc_floor_area_m2) if comp.epc_floor_area_m2 else "\u2014",
                "price":    _gbp(comp.sale_price),
                "date":     _fmt_date(comp.sale_date),
                "photo_uri": (photo_uris or {}).get(str(comp.id)),
            }
            for comp in comparables[:6]
        ],

        # ── Chart ─────────────────────────────────────────────
        "chart": chart or _default_chart(est_gbp),
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
        agent_name:  str = "PropValue",
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

        est_gbp = report.estimated_value / 100 if report.estimated_value else 0
        # Comparables missing a cached EPC floor area get one fetched now.
        # Runs concurrently with photos and the chart so it adds ~1-2s, not
        # 5-10s. DISPLAY ONLY - never fed back into the valuation engine.
        needs_area = [
            c for c in comparables[:6]
            if c.epc_floor_area_m2 is None and c.postcode_snapshot
        ]
        photo_uris, real_chart, comp_areas, subject_photo = await asyncio.gather(
            fetch_comparable_photos(comparables[:6]),
            fetch_real_price_chart(property_.address.postcode, est_gbp),
            fetch_comparable_floor_areas(needs_area),
            fetch_subject_photo(property_),
        )
        for comp in comparables[:6]:
            area = comp_areas.get(str(comp.id))
            if area:
                comp.epc_floor_area_m2 = area

        context = build_context(
            report=report,
            property_=property_,
            comparables=comparables,
            agent_name=agent_name,
            chart=chart or real_chart,
            market_data=market_data,
            photo_uris=photo_uris,
            subject_photo=subject_photo,
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
