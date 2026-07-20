"""FastAPI auth dependencies.

- ``get_current_user`` resolves the ``Authorization: Bearer`` credential — an API
  key (enterprise tier, #24) by its prefix, otherwise a JWT — into tenant/user
  context. This is the seam every protected route hangs off; per-tenant tier
  limits (#25) extend it without touching the routes themselves.
- ``enforce_rate_limit`` / ``enforce_auth_rate_limit`` are in-process sliding-
  window limiters (#85, #140): a per-client burst cap on ``/query`` and a
  stricter cap on the auth endpoints. Per-tenant tier limits arrive in #25.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.auth.api_keys import hash_api_key, looks_like_api_key
from src.auth.rate_limit import SlidingWindowLimiter
from src.auth.tokens import TokenError, decode_access_token
from src.config import Settings, get_settings
from src.db import connect
from src.db.api_keys import get_active_api_key_by_hash, touch_last_used

logger = logging.getLogger(__name__)


class CurrentUser(BaseModel):
    """Tenant/user context extracted from a verified credential."""

    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Resolve the bearer credential (API key or JWT) into tenant/user context.

    Every failure mode maps to the same opaque ``401 unauthorized`` — the caller
    is never told whether the header was missing, malformed, expired, or forged.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized()
    token = authorization[7:].strip()
    if not token:
        raise _unauthorized()
    if looks_like_api_key(token):
        return await _authenticate_api_key(settings, token)
    try:
        claims = decode_access_token(token, settings.jwt_secret)
    except TokenError:
        raise _unauthorized() from None
    return CurrentUser(tenant_id=claims.tenant_id, user_id=claims.sub)


async def _authenticate_api_key(settings: Settings, raw_key: str) -> CurrentUser:
    """Resolve an enterprise API key to its tenant.

    API-key requests are not tied to a user, so ``user_id`` is None (the
    ``query_logs.user_id`` column is nullable to allow exactly this).
    """
    key_hash = hash_api_key(raw_key)
    async with connect(settings.database_url) as conn:
        record = await get_active_api_key_by_hash(conn, key_hash)
        if record is None:
            raise _unauthorized()
        try:
            await touch_last_used(conn, record.id)
        except Exception:  # noqa: BLE001 — last_used is best-effort, never blocks auth
            logger.warning("api_key last_used update failed", exc_info=True)
    return CurrentUser(tenant_id=record.tenant_id, user_id=None)


# ─── Per-client rate limiting (#85, #140) ────────────────────────────────────
#
# ``/query`` and the auth endpoints each own a separate limiter instance, so
# their counters never interfere. Tier-aware quotas are ``enforce_tier_limit``.

_RATE_WINDOW_SECONDS = 60.0

_query_limiter = SlidingWindowLimiter(window_seconds=_RATE_WINDOW_SECONDS)
_auth_limiter = SlidingWindowLimiter(window_seconds=_RATE_WINDOW_SECONDS)

# Back-compat alias: existing tests reset limiter state via ``_request_log.clear()``.
# It must remain the *same object* as the query limiter's bucket dict.
_request_log = _query_limiter._buckets


def _client_key(request: Request, hops: int) -> str:
    """Identify the caller by the trusted client IP.

    Traefik *appends* the true socket peer as the right-most ``X-Forwarded-For``
    entry, so the trusted client is the ``hops``-th entry counted from the right
    (``hops`` = number of trusted reverse-proxy hops). A client-supplied leading
    value is attacker-controlled and is never used.

    - ``hops == 0`` (no proxy): use the direct peer IP.
    - Fewer XFF entries than ``hops`` (request did not traverse the trusted proxy
      chain) or XFF absent: fall back to the peer IP — never trust a partial XFF.
    """
    peer = request.client.host if request.client else "unknown"
    if hops <= 0:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
    if len(entries) < hops:
        return peer
    return entries[-hops]


def _reject_over_limit(detail: str) -> HTTPException:
    return HTTPException(status_code=429, detail=detail, headers={"Retry-After": "60"})


async def enforce_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Sliding-window per-client burst limit on ``/query`` (429 above threshold).

    Disabled when ``query_rate_limit_per_minute`` is 0. In-process state is
    sufficient for the current single-replica deployment.
    """
    key = _client_key(request, settings.trusted_proxy_hops)
    allowed = _query_limiter.check(
        key,
        limit=settings.query_rate_limit_per_minute,
        now=time.monotonic(),
        max_keys=settings.rate_limit_max_keys,
    )
    if not allowed:
        raise _reject_over_limit("Rate limit exceeded; try again shortly.")


async def enforce_auth_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Stricter per-client limit on ``/auth/login`` + ``/auth/refresh`` (#140).

    Runs as a route dependency *before* the credential/CSRF checks, so failed
    login attempts are counted — bounding online password brute-force. Disabled
    when ``auth_rate_limit_per_minute`` is 0.
    """
    key = _client_key(request, settings.trusted_proxy_hops)
    allowed = _auth_limiter.check(
        key,
        limit=settings.auth_rate_limit_per_minute,
        now=time.monotonic(),
        max_keys=settings.rate_limit_max_keys,
    )
    if not allowed:
        raise _reject_over_limit("Too many authentication attempts; try again shortly.")
