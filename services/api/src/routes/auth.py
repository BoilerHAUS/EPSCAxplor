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


@router.post("/refresh", response_model=TokenResponse)
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


@router.post("/logout")
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
