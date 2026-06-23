"""
Clerk authentication for FastAPI.

Verifies Clerk session JWTs (RS256) against Clerk's public JWKS endpoint —
no Clerk secret key needed on the backend for this. Resolves the
corresponding internal `User` row by `clerk_id`, creating one on first
sign-in (get-or-create).
"""
import time
from typing import Annotated

import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from db.session import get_db
from models.orm import User

logger = structlog.get_logger(__name__)
settings = get_settings()

_security = HTTPBearer(auto_error=False)

_jwks_cache: dict | None = None
_jwks_cache_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


async def _fetch_jwks(*, force: bool = False) -> dict:
    global _jwks_cache, _jwks_cache_at
    now = time.time()
    if force or _jwks_cache is None or (now - _jwks_cache_at) > _JWKS_TTL_SECONDS:
        url = f"https://{settings.CLERK_FRONTEND_API}/.well-known/jwks.json"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_at = now
    return _jwks_cache


async def _verify_clerk_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token header") from exc

    jwks = await _fetch_jwks()
    key = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
    if key is None:
        jwks = await _fetch_jwks(force=True)
        key = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
        if key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unable to verify token signature")

    try:
        claims = jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc
    return claims


async def _get_or_create_user(db: AsyncSession, claims: dict) -> User:
    clerk_id = claims.get("sub")
    if not clerk_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing subject claim")

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        clerk_id=clerk_id,
        email=claims.get("email"),
        full_name=claims.get("full_name") or claims.get("name"),
    )
    db.add(user)
    await db.flush()
    logger.info("user_created_from_clerk", clerk_id=clerk_id)
    return user


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
) -> User:
    """Required auth — raises 401 if no valid session token is present."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    claims = await _verify_clerk_token(credentials.credentials)
    return await _get_or_create_user(db, claims)


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
) -> User | None:
    """Optional auth — returns None instead of raising if not signed in."""
    if credentials is None:
        return None
    try:
        claims = await _verify_clerk_token(credentials.credentials)
    except HTTPException:
        return None
    return await _get_or_create_user(db, claims)
