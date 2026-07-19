"""Auth routes: login, refresh, logout (#23).

Session flow (planning.md §10): login returns a short-lived access JWT in the
body and a long-lived opaque refresh token in an httpOnly cookie; refresh rotates
that cookie; logout revokes it. The access token is what protected routes verify
via ``get_current_user``.

Cookie note: cookies set on the injected ``Response`` are dropped when a handler
raises, so error paths that must *clear* the cookie return an explicit response.
"""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.auth.service import (
    AuthError,
    login,
    revoke_refresh_token,
    rotate_refresh_token,
)
from src.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

# Refresh cookie is scoped to /auth so it is only sent to the token endpoints.
_REFRESH_COOKIE_PATH = "/auth"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 scheme label, not a secret
    expires_in: int


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Sec-Fetch-Site values that indicate a non-cross-site request.  "none" means
# a user-initiated navigation (address bar, bookmark), which cannot be forged
# by an attacker's page.
_SAFE_FETCH_SITES = frozenset({"same-origin", "same-site", "none"})


def _allowed_origins(cors_origins: str) -> set[str]:
    """Normalised origin allow-list from the comma-separated CORS_ORIGINS."""
    return {
        origin.strip().rstrip("/").lower()
        for origin in cors_origins.split(",")
        if origin.strip()
    }


def _is_same_host(origin: str, host: str | None) -> bool:
    """True when *origin*'s authority equals the request's own Host header.

    Lets same-origin callers (e.g. Swagger UI served by the API itself) pass
    without being listed in CORS_ORIGINS.  A cross-site attacker cannot make
    the victim's browser send a matching pair: the browser pins Origin to the
    attacker's page and Host to the target API.

    Trust note: this relies on the API container being reachable only via
    Traefik, whose Host-based routing guarantees the header matches the real
    API hostname (prod compose exposes no host port).  If a direct ingress
    path is ever added, the raw Host header becomes attacker-controlled and
    this shortcut must be revisited.
    """
    if not host:
        return False
    return urlsplit(origin).netloc.lower() == host.strip().lower()


async def enforce_csrf_origin(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject cross-site browser requests to cookie-authenticated routes (#104).

    ``/auth/refresh`` and ``/auth/logout`` are authenticated solely by the
    httpOnly refresh cookie, so a cross-site auto-submitting form (top-level
    navigation attaches SameSite=Lax cookies) could force-logout a victim.
    Browsers always attach ``Origin`` to cross-site POSTs, so verifying it
    against CORS_ORIGINS blocks the attack; ``Sec-Fetch-Site`` covers agents
    that send fetch metadata without an Origin.  Requests with neither header
    (curl, tests, server-to-server) pass — they cannot carry a victim's
    browser cookie in the first place.
    """
    origin = request.headers.get("origin")
    if origin is not None:
        normalised = origin.strip().rstrip("/").lower()
        if normalised in _allowed_origins(settings.cors_origins) or _is_same_host(
            origin, request.headers.get("host")
        ):
            return
        raise HTTPException(status_code=403, detail="cross-site request rejected")

    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site is not None and fetch_site.strip().lower() not in _SAFE_FETCH_SITES:
        raise HTTPException(status_code=403, detail="cross-site request rejected")


def _set_refresh_cookie(response: Response, settings: Settings, raw_refresh: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_refresh,
        max_age=settings.jwt_refresh_expiry_days * 86_400,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=_REFRESH_COOKIE_PATH,
        domain=settings.refresh_cookie_domain,
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=_REFRESH_COOKIE_PATH,
        domain=settings.refresh_cookie_domain,
    )


@router.post("/login", response_model=TokenResponse)
async def login_route(
    body: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """Authenticate email + password; issue an access token and refresh cookie."""
    try:
        pair = await login(settings, body.email, body.password)
    except AuthError:
        raise _unauthorized() from None
    _set_refresh_cookie(response, settings, pair.refresh_token)
    return TokenResponse(access_token=pair.access_token, expires_in=pair.expires_in)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_csrf_origin)],
)
async def refresh_route(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse | JSONResponse:
    """Rotate the refresh cookie and mint a new access token."""
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    try:
        pair = await rotate_refresh_token(settings, raw)
    except AuthError:
        # Clear the now-useless (possibly compromised) cookie on the error response.
        cleared = JSONResponse(status_code=401, content={"detail": "unauthorized"})
        _clear_refresh_cookie(cleared, settings)
        return cleared
    _set_refresh_cookie(response, settings, pair.refresh_token)
    return TokenResponse(access_token=pair.access_token, expires_in=pair.expires_in)


@router.post("/logout", dependencies=[Depends(enforce_csrf_origin)])
async def logout_route(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Revoke the refresh-token family and clear the cookie. Idempotent (204)."""
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        await revoke_refresh_token(settings, raw)
    resp = Response(status_code=204)
    _clear_refresh_cookie(resp, settings)
    return resp
