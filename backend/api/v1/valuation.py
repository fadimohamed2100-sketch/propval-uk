import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from api.deps import get_valuation_service
from core.exceptions import ReportNotReadyError
from schemas.schemas import ComparableOut, ValuationDetailOut, ValuationOut, ValuationRequest
from services.valuation_service import ValuationService

router = APIRouter(prefix="/valuation", tags=["Valuation"])


def _to_gbp(pence: int | None) -> float | None:
    return round(pence / 100, 2) if pence is not None else None


def _serialise_valuation(report, *, include_property: bool = False):
    """Shared serialisation for ValuationOut / ValuationDetailOut."""
    comps = [
        ComparableOut.model_validate(
            {
                **{c: getattr(comp, c) for c in comp.__table__.columns.keys()},
                "sale_price_gbp": _to_gbp(comp.sale_price),
                "price_per_m2_gbp": _to_gbp(comp.price_per_m2),
            }
        )
        for comp in (report.comparables or [])
    ]

    base = {
        "id": report.id,
        "property_id": report.property_id,
        "status": report.status,
        "estimated_value_gbp": _to_gbp(report.estimated_value),
        "range_low_gbp": _to_gbp(report.range_low),
        "range_high_gbp": _to_gbp(report.range_high),
        "confidence_score": float(report.confidence_score) if report.confidence_score else None,
        "rental_monthly_gbp": _to_gbp(report.rental_monthly),
        "rental_yield": float(report.rental_yield) if report.rental_yield else None,
        "source_apis": report.source_apis or [],
        "comparables": comps,
        "pdf_url": (
            f"/api/v1/valuation/{report.id}/report" if report.pdf_path else None
        ),
        "created_at": report.created_at,
        "expires_at": report.expires_at,
    }

    if include_property:
        try:
            prop = report.property
            if prop and prop.address:
                base["property"] = {
                    "id": str(prop.id),
                    "property_type": prop.property_type,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "floor_area_m2": float(prop.floor_area_m2) if prop.floor_area_m2 else None,
                    "epc_rating": prop.epc_rating,
                    "address": {
                        "address_norm": prop.address.address_norm,
                        "postcode": prop.address.postcode,
                        "display_address": prop.address.address_norm,
                    },
                }
            else:
                base["property"] = None
        except Exception as e:
            logger.warning("property_serialise_error", error=str(e))
            base["property"] = None
        base["methodology"] = report.methodology or {}
        return ValuationDetailOut.model_validate(base)

    return ValuationOut.model_validate(base)


# ---------------------------------------------------------------
# POST /valuation/run
# ---------------------------------------------------------------
@router.post(
    "/run",
    response_model=ValuationDetailOut,
    status_code=200,
    summary="Run a full property valuation for a given address",
)
async def run_valuation(
    body: ValuationRequest,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
) -> ValuationDetailOut:
    """
    Full pipeline:
    1. Geocode address
    2. Enrich from EPC register
    3. Fetch comparable sales (Land Registry)
    4. Run the valuation engine
    5. Return complete report with comparables

    Set `force_refresh: true` to bypass the 30-day cache.
    """
    report = await svc.run_valuation(
        raw_address=body.address,
        force_refresh=body.force_refresh,
        bedrooms=body.bedrooms,
        bathrooms=body.bathrooms,
        condition=body.condition,
        parking=body.parking,
        outdoor_space=body.outdoor_space,
        property_type=body.property_type,
        tenure=body.tenure,
        lease_years=body.lease_years,
    )
    return _serialise_valuation(report, include_property=True)


# ---------------------------------------------------------------
# GET /valuation/{id}
# ---------------------------------------------------------------
@router.get(
    "/{valuation_id}",
    response_model=ValuationDetailOut,
    summary="Retrieve a valuation report by ID",
)
async def get_valuation(
    valuation_id: uuid.UUID,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
) -> ValuationDetailOut:
    """
    Returns the full valuation including property details,
    all comparables, and the methodology breakdown.
    """
    report = await svc.get_valuation(valuation_id)
    return _serialise_valuation(report, include_property=True)


# ---------------------------------------------------------------
# GET /valuation/{id}/report
# ---------------------------------------------------------------
@router.get(
    "/{valuation_id}/report",
    summary="Download the branded PDF report",
    response_class=FileResponse,
)
async def download_report(
    valuation_id: uuid.UUID,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
) -> FileResponse:
    """
    Streams the pre-generated PDF to the client.
    Returns 409 if the PDF is not yet ready.
    """
    report = await svc.get_valuation(valuation_id)

    if not report.pdf_path or not os.path.exists(report.pdf_path):
        raise ReportNotReadyError(str(valuation_id))

    filename = f"valuation_{valuation_id}.pdf"
    return FileResponse(
        path=report.pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
