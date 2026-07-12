"""FastAPI auth dependencies.

- ``get_current_user`` decodes the access JWT from the ``Authorization`` header
  and yields the tenant/user context. This is the seam every protected route
  hangs off; API-key auth (#24) and tier limits (#25) extend it without touching
  the routes themselves.
- ``enforce_rate_limit`` is the interim in-process sliding-window limiter from
  #85, kept verbatim (per-tenant tier limits arrive in #25).
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.auth.tokens import TokenError, decode_access_token
from src.config import Settings, get_settings


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
    """Require a valid access JWT and return the tenant/user context.

    Every failure mode maps to the same opaque ``401 unauthorized`` — the caller
    is never told whether the header was missing, malformed, expired, or forged.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _unauthorized()
    token = authorization[7:].strip()
    if not token:
        raise _unauthorized()
    try:
        claims = decode_access_token(token, settings.jwt_secret)
    except TokenError:
        raise _unauthorized() from None
    return CurrentUser(tenant_id=claims.tenant_id, user_id=claims.sub)


# ─── Interim rate limiting (#85); tier-aware limits arrive in #25 ─────────────

_RATE_WINDOW_SECONDS = 60.0
# Per-client request timestamps within the sliding window.
_request_log: dict[str, deque[float]] = {}


def _client_key(request: Request) -> str:
    """Identify the caller: first X-Forwarded-For hop (Traefik) or peer IP."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Sliding-window per-client rate limit (429 above the threshold).

    Disabled when ``query_rate_limit_per_minute`` is 0. In-process state is
    sufficient for the current single-replica deployment.
    """
    limit = settings.query_rate_limit_per_minute
    if limit <= 0:
        return

    now = time.monotonic()
    key = _client_key(request)
    window = _request_log.setdefault(key, deque())
    while window and now - window[0] > _RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded; try again shortly.",
            headers={"Retry-After": "60"},
        )
    window.append(now)
