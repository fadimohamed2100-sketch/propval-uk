import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from core.limiter import limiter
from db.session import get_db
from services.credit_service import CreditService
from api.deps import get_valuation_service
from db.session import get_db
from models.orm import Property, User, ValuationReport
from schemas.schemas import (
    ComparableOut,
    ValuationDetailOut,
    ValuationHistoryItemOut,
    ValuationOut,
    ValuationRequest,
)
from services.valuation_service import ValuationService
from sqlalchemy.ext.asyncio import AsyncSession

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
                base["methodology"] = {
                    **(report.methodology or {}),
                    "address_norm": prop.address.address_norm,
                    "postcode": prop.address.postcode,
                }
            else:
                base["methodology"] = report.methodology or {}
        except Exception:
            base["methodology"] = report.methodology or {}
        base["property"] = None
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
@limiter.limit("10/minute")
async def run_valuation(
    request: Request,
    body: ValuationRequest,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValuationDetailOut:
    """
    Full pipeline:
    1. Geocode address
    2. Enrich from EPC register
    3. Fetch comparable sales (Land Registry)
    4. Run the valuation engine
    5. Return complete report with comparables

    Requires a signed-in user (Clerk session token in the Authorization header).
    Set `force_refresh: true` to bypass the 30-day cache.
    """
    # Pre-charge 1 credit atomically (fails fast with 402 before any paid
    # external API call is made). If the valuation raises, the whole request
    # transaction rolls back - charge included. If it returns a CACHED
    # report (created before this request started), the credit is refunded:
    # agents are never charged twice for the same computation.
    request_start = datetime.now(timezone.utc)
    credit_svc = CreditService(db)
    await credit_svc.spend(current_user, 1, "valuation")

    report = await svc.run_valuation(
        raw_address=body.address,
        user_id=current_user.id,
        force_refresh=body.force_refresh,
        bedrooms=body.bedrooms,
        bathrooms=body.bathrooms,
        receptions=body.receptions,
        construction_date=body.construction_date,
        condition=body.condition,
        parking=body.parking,
        outdoor_space=body.outdoor_space,
        property_type=body.property_type,
        tenure=body.tenure,
        lease_years=body.lease_years,
        unit_identifier=body.unit_identifier,
        uprn=body.uprn,
    )
    if report.created_at < request_start:
        await credit_svc.refund(
            current_user, 1, "valuation_cache_refund", report_id=report.id
        )
    return _serialise_valuation(report, include_property=True)


# ---------------------------------------------------------------
# GET /valuation/history
# ---------------------------------------------------------------
@router.get(
    "/history",
    response_model=list[ValuationHistoryItemOut],
    summary="List the signed-in user's past valuations, most recent first",
)
async def get_valuation_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ValuationHistoryItemOut]:
    stmt = (
        select(ValuationReport)
        .where(ValuationReport.user_id == current_user.id)
        .options(
            selectinload(ValuationReport.property).selectinload(Property.address)
        )
        .order_by(ValuationReport.created_at.desc())
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()

    items: list[ValuationHistoryItemOut] = []
    for report in reports:
        addr = report.property.address if report.property else None
        address_line = ", ".join(
            filter(None, [addr.line_1, addr.line_2, addr.city] if addr else [])
        ) or "Unknown address"
        items.append(
            ValuationHistoryItemOut(
                id=report.id,
                address_line=address_line,
                postcode=addr.postcode if addr else "",
                estimated_value_gbp=_to_gbp(report.estimated_value),
                range_low_gbp=_to_gbp(report.range_low),
                range_high_gbp=_to_gbp(report.range_high),
                confidence_score=float(report.confidence_score) if report.confidence_score else None,
                status=report.status,
                pdf_url=f"/api/v1/valuation/{report.id}/report" if report.pdf_path else None,
                created_at=report.created_at,
            )
        )
    return items


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
@limiter.limit("10/minute")
async def download_report(
    request: Request,
    valuation_id: uuid.UUID,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: bool = False,
) -> FileResponse:
    """
    Generates the branded PDF report on first request (a few seconds,
    since it renders via headless Chromium), then serves the cached
    file on every subsequent download for the same valuation.

    Pass `?force=true` to bypass the cache and regenerate from the
    current data (e.g. after correcting a data issue retroactively).
    """
    report = await svc.get_valuation(valuation_id)

    # PDF costs 2 additional credits (3 total with the 1-credit valuation),
    # charged ONCE per report: re-downloads and regenerations of an
    # already-paid report are free. If generation fails after charging,
    # the request transaction rolls back and the charge is undone.
    credit_svc = CreditService(db)
    if not await credit_svc.has_paid_for_pdf(valuation_id):
        await credit_svc.spend(current_user, 2, "pdf_download", report_id=valuation_id)

    pdf_path = await svc.get_or_generate_report_pdf(valuation_id, force=force)

    addr = report.property.address if report.property else None
    address_line = ", ".join(
        filter(None, [addr.line_1, addr.line_2, addr.city] if addr else [])
    )
    postcode = addr.postcode if addr else ""
    raw_name = f"{address_line} {postcode} valuation".strip()
    safe_name = re.sub(r"[^\w\s-]", "", raw_name)
    safe_name = re.sub(r"\s+", " ", safe_name).strip()
    filename = f"{safe_name or f'valuation_{valuation_id}'}.pdf"

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
