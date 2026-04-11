"""
PDF report generator.
Renders a Jinja2 HTML template to PDF via WeasyPrint.
"""
import os
import uuid
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from core.config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _build_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


_jinja_env = _build_jinja_env()


def generate_report_pdf(valuation_data: dict) -> str:
    """
    Renders the valuation report as a PDF and saves it to REPORTS_DIR.

    Args:
        valuation_data: dict with all template variables.

    Returns:
        Absolute file path to the saved PDF.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        logger.warning("weasyprint_not_installed — returning mock path")
        return _mock_pdf_path(valuation_data.get("valuation_id", "unknown"))

    os.makedirs(settings.REPORTS_DIR, exist_ok=True)

    template = _jinja_env.get_template("report.html")
    html_content = template.render(**valuation_data)

    filename = f"valuation_{valuation_data.get('valuation_id', uuid.uuid4())}.pdf"
    output_path = os.path.join(settings.REPORTS_DIR, filename)

    HTML(string=html_content, base_url=str(_TEMPLATES_DIR)).write_pdf(output_path)
    logger.info("pdf_generated", path=output_path)
    return output_path


def _mock_pdf_path(valuation_id: str) -> str:
    """Development fallback when WeasyPrint is not installed."""
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    path = os.path.join(settings.REPORTS_DIR, f"valuation_{valuation_id}.pdf")
    Path(path).write_text(f"Mock PDF for valuation {valuation_id}")
    return path


def build_report_context(valuation, property_, address, comparables) -> dict:
    """
    Builds the template context dict from ORM objects.
    All money values are converted to pounds for display.
    """
    def p2gbp(pence: int | None) -> str:
        if pence is None:
            return "N/A"
        return f"£{pence / 100:,.0f}"

    return {
        "valuation_id": str(valuation.id),
        "report_date": valuation.created_at.strftime("%d %B %Y"),
        "address_line_1": address.line_1,
        "address_line_2": address.line_2 or "",
        "city": address.city,
        "postcode": address.postcode,
        "property_type": (property_.property_type or "").replace("_", " ").title(),
        "bedrooms": property_.bedrooms,
        "bathrooms": property_.bathrooms,
        "floor_area_m2": property_.floor_area_m2,
        "epc_rating": property_.epc_rating or "N/A",
        "tenure": (property_.tenure or "N/A").replace("_", " ").title(),
        "estimated_value": p2gbp(valuation.estimated_value),
        "range_low": p2gbp(valuation.range_low),
        "range_high": p2gbp(valuation.range_high),
        "confidence_score": f"{valuation.confidence_score * 100:.0f}%",
        "rental_monthly": p2gbp(valuation.rental_monthly),
        "rental_yield": f"{valuation.rental_yield or 0:.1f}%",
        "comparables": [
            {
                "address": c.address_snapshot,
                "sale_price": p2gbp(c.sale_price),
                "sale_date": c.sale_date.strftime("%b %Y") if c.sale_date else "",
                "distance_m": c.distance_m,
                "property_type": (c.property_type or "").replace("_", " ").title(),
                "bedrooms": c.bedrooms,
            }
            for c in comparables
        ],
        "methodology": valuation.methodology,
    }
