"""Credits API — balance lookup for the signed-in user."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from db.session import get_db
from models.orm import User
from services.credit_service import CreditService

router = APIRouter(prefix="/credits", tags=["Credits"])


@router.get("", summary="Get the signed-in user's credit balance")
async def get_credits(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    svc = CreditService(db)
    balance = await svc.get_balance(current_user)
    return {
        "credits_remaining": balance["credits_remaining"],
        "subscription_tier": balance["subscription_tier"],
        "credits_reset_at": (
            balance["credits_reset_at"].isoformat()
            if balance["credits_reset_at"] else None
        ),
        "costs": {"valuation": 1, "pdf_additional": 2, "pdf_total_with_valuation": 3},
    }
