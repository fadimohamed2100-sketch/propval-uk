"""
CreditService — atomic credit accounting.

Design principles:
- The users.credits_remaining column is the single source of truth.
- Every change goes through an atomic conditional UPDATE
  (credits_remaining = credits_remaining - N WHERE credits_remaining >= N),
  so two concurrent requests can never overspend a balance.
- Every change writes a CreditTransaction ledger row (amount signed,
  balance_after recorded) so support disputes and usage analytics are
  always answerable from the database alone.

Pricing (see core/config.py):
  valuation        = 1 credit
  PDF download     = 2 additional credits (3 total with the valuation)
  PDF re-downloads = free once paid for a given report
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import InsufficientCreditsError
from core.logging import get_logger
from models.orm import CreditTransaction, User

logger = get_logger(__name__)


class CreditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_balance(self, user: User) -> dict:
        """Fresh read of the user's balance straight from the DB."""
        result = await self._db.execute(
            select(User.credits_remaining, User.subscription_tier, User.credits_reset_at)
            .where(User.id == user.id)
        )
        row = result.one()
        return {
            "credits_remaining": row.credits_remaining,
            "subscription_tier": row.subscription_tier,
            "credits_reset_at": row.credits_reset_at,
        }

    async def spend(
        self,
        user: User,
        amount: int,
        reason: str,
        report_id: uuid.UUID | None = None,
    ) -> int:
        """
        Atomically deduct `amount` credits. Raises InsufficientCreditsError
        (HTTP 402) if the balance is too low — the conditional UPDATE makes
        this race-safe under concurrent requests. Returns the new balance.
        """
        result = await self._db.execute(
            text(
                """
                UPDATE users
                SET credits_remaining = credits_remaining - :amount
                WHERE id = :user_id AND credits_remaining >= :amount
                RETURNING credits_remaining
                """
            ),
            {"amount": amount, "user_id": str(user.id)},
        )
        row = result.fetchone()
        if row is None:
            balance = (await self.get_balance(user))["credits_remaining"]
            logger.info(
                "credit_spend_rejected",
                user_id=str(user.id), needed=amount, balance=balance, reason=reason,
            )
            raise InsufficientCreditsError(needed=amount, balance=balance)

        new_balance = row[0]
        self._db.add(CreditTransaction(
            user_id=user.id,
            amount=-amount,
            balance_after=new_balance,
            reason=reason,
            report_id=report_id,
        ))
        await self._db.flush()
        logger.info(
            "credit_spent",
            user_id=str(user.id), amount=amount, reason=reason,
            balance_after=new_balance, report_id=str(report_id) if report_id else None,
        )
        return new_balance

    async def refund(
        self,
        user: User,
        amount: int,
        reason: str,
        report_id: uuid.UUID | None = None,
    ) -> int:
        """
        Return credits (e.g. a pre-charged valuation turned out to be a
        cache hit, or PDF generation failed after charging).
        """
        result = await self._db.execute(
            text(
                """
                UPDATE users
                SET credits_remaining = credits_remaining + :amount
                WHERE id = :user_id
                RETURNING credits_remaining
                """
            ),
            {"amount": amount, "user_id": str(user.id)},
        )
        new_balance = result.fetchone()[0]
        self._db.add(CreditTransaction(
            user_id=user.id,
            amount=amount,
            balance_after=new_balance,
            reason=reason,
            report_id=report_id,
        ))
        await self._db.flush()
        logger.info(
            "credit_refunded",
            user_id=str(user.id), amount=amount, reason=reason, balance_after=new_balance,
        )
        return new_balance

    async def has_paid_for_pdf(self, report_id: uuid.UUID) -> bool:
        """
        True if any successful (non-refunded) PDF charge exists for this
        report — used so re-downloads and regenerations stay free once paid.
        """
        result = await self._db.execute(
            select(CreditTransaction.id)
            .where(
                CreditTransaction.report_id == report_id,
                CreditTransaction.reason == "pdf_download",
                CreditTransaction.amount < 0,
            )
            .limit(1)
        )
        return result.first() is not None
