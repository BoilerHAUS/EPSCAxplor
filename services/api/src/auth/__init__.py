"""Auth module — Phase 1/2 interim protection.

Provides two FastAPI dependencies used by the query route:

- ``get_current_user`` — when ``QUERY_API_TOKEN`` is configured, requires
  ``Authorization: Bearer <token>``; otherwise accepts all requests (the
  original Phase 1 stub behaviour, so nothing breaks before the env var is
  set in Dokploy).  Real JWT auth replaces this in Phase 3 (#23).
- ``enforce_rate_limit`` — sliding-window per-client limit so an exposed
  endpoint cannot rack up unbounded Claude API spend (#85).
"""

from __future__ import annotations

import secrets
import time
import uuid
from collections import deque
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.config import Settings, get_settings

# Hardcoded system tenant UUID used for query logging until real auth is active.
# Must be seeded in the tenants table before query_logs writes succeed.
SYSTEM_TENANT_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_RATE_WINDOW_SECONDS = 60.0
# Per-client request timestamps within the sliding window.
_request_log: dict[str, deque[float]] = {}


class CurrentUser(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None


async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Interim auth: require the shared bearer token when one is configured.

    Token comparison uses ``secrets.compare_digest`` to avoid timing leaks.
    When ``query_api_token`` is unset the endpoint remains open (pre-#85
    behaviour) so deploys without the env var don't lock everyone out.
    """
    token = settings.query_api_token
    if token:
        provided = ""
        if authorization and authorization.lower().startswith("bearer "):
            provided = authorization[7:].strip()
        if not provided or not secrets.compare_digest(provided, token):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return CurrentUser(tenant_id=SYSTEM_TENANT_ID)


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

    Disabled when ``query_rate_limit_per_minute`` is 0.  In-process state is
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
