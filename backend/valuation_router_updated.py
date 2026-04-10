"""
Valuation API routes.

GET /valuation/{id}/pdf  — generates (or serves cached) Playwright PDF
POST /valuation/run      — run a full valuation
GET  /valuation/{id}     — retrieve a saved valuation
"""
import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.deps import get_db, get_valuation_service
from core.exceptions import ReportNotReadyError, ValuationNotFoundError
from schemas.schemas import ComparableOut, ValuationDetailOut, ValuationOut, ValuationRequest
from services.valuation_service import ValuationService
from services.pdf_playwright import PlaywrightPDFService
from models.orm import Comparable, Property, ValuationReport

router = APIRouter(prefix="/valuation", tags=["Valuation"])


# ── Shared helpers ────────────────────────────────────────────

def _to_gbp(pence: int | None) -> float | None:
    return round(pence / 100, 2) if pence is not None else None


def _serialise(report, *, include_property: bool = False):
    comps = [
        ComparableOut.model_validate({
            **{c: getattr(comp, c) for c in comp.__table__.columns.keys()},
            "sale_price_gbp":   _to_gbp(comp.sale_price),
            "price_per_m2_gbp": _to_gbp(comp.price_per_m2),
        })
        for comp in (report.comparables or [])
    ]

    base = {
        "id":                   report.id,
        "property_id":          report.property_id,
        "status":               report.status,
        "estimated_value_gbp":  _to_gbp(report.estimated_value),
        "range_low_gbp":        _to_gbp(report.range_low),
        "range_high_gbp":       _to_gbp(report.range_high),
        "confidence_score":     float(report.confidence_score) if report.confidence_score else None,
        "rental_monthly_gbp":   _to_gbp(report.rental_monthly),
        "rental_yield":         float(report.rental_yield) if report.rental_yield else None,
        "source_apis":          report.source_apis or [],
        "comparables":          comps,
        "pdf_url":              f"/api/v1/valuation/{report.id}/pdf",
        "created_at":           report.created_at,
        "expires_at":           report.expires_at,
    }
    if include_property:
        base["property"]    = report.property
        base["methodology"] = report.methodology or {}
        return ValuationDetailOut.model_validate(base)
    return ValuationOut.model_validate(base)


# ── POST /valuation/run ───────────────────────────────────────

@router.post(
    "/run",
    response_model=ValuationDetailOut,
    summary="Run a full property valuation",
)
async def run_valuation(
    body: ValuationRequest,
    svc:  Annotated[ValuationService, Depends(get_valuation_service)],
) -> ValuationDetailOut:
    report = await svc.run_valuation(
        raw_address=body.address,
        force_refresh=body.force_refresh,
    )
    return _serialise(report, include_property=True)


# ── GET /valuation/{id} ───────────────────────────────────────

@router.get(
    "/{valuation_id}",
    response_model=ValuationDetailOut,
    summary="Retrieve a valuation by ID",
)
async def get_valuation(
    valuation_id: uuid.UUID,
    svc: Annotated[ValuationService, Depends(get_valuation_service)],
) -> ValuationDetailOut:
    report = await svc.get_valuation(valuation_id)
    return _serialise(report, include_property=True)


# ── GET /valuation/{id}/pdf ───────────────────────────────────

@router.get(
    "/{valuation_id}/pdf",
    summary="Download the branded A4 PDF report",
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "A4 branded PDF report.",
        },
        404: {"description": "Valuation not found."},
        409: {"description": "Valuation is still processing."},
        502: {"description": "PDF generation failed."},
    },
)
async def download_pdf(
    valuation_id: uuid.UUID,
    svc:  Annotated[ValuationService, Depends(get_valuation_service)],
    db:   Annotated[object,           Depends(get_db)],
) -> FileResponse:
    """
    Generates (or serves a cached) Playwright PDF for the valuation.

    First call renders the HTML → PDF via headless Chromium (~2–4 s).
    Subsequent calls return the cached file instantly.

    Force regeneration by appending `?refresh=1`.
    """
    # 1. Load the report with comparables and property
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(ValuationReport)
        .where(ValuationReport.id == valuation_id)
        .options(
            selectinload(ValuationReport.comparables),
            selectinload(ValuationReport.property).selectinload(Property.address),
        )
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise ValuationNotFoundError(str(valuation_id))

    if report.status != "complete":
        raise ReportNotReadyError(str(valuation_id))

    # 2. Generate PDF (cached on disk after first render)
    pdf_service = PlaywrightPDFService()
    try:
        pdf_path = await pdf_service.generate(
            report=report,
            property_=report.property,
            comparables=report.comparables or [],
        )
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=str(exc))

    # 3. Persist the path on the report row (fire-and-forget)
    if not report.pdf_path:
        report.pdf_path = str(pdf_path)
        await db.flush()

    # 4. Stream the file
    filename = f"valuation_{str(valuation_id)[:8]}.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control":       "private, max-age=3600",
        },
    )
