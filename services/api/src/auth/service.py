"""Auth orchestration: authenticate, issue token pairs, rotate with reuse
detection, and revoke.

This layer bridges settings -> primitives (passwords/tokens) -> db access, and
owns the transaction boundaries. Refresh-token rotation is the security-critical
path: rotating a token marks the old one spent and issues a child in the same
family; presenting an already-spent token is treated as theft and burns the
whole family.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from src.auth.passwords import hash_password, verify_password
from src.auth.tokens import (
    encode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from src.config import Settings
from src.db import connect
from src.db.tokens import (
    get_refresh_token_by_hash,
    insert_refresh_token,
    mark_rotated,
    revoke_family,
)
from src.db.users import UserRecord, get_user_by_email, get_user_by_id, touch_last_login


class AuthError(Exception):
    """Authentication failed. The message is intentionally uniform so callers
    cannot distinguish 'unknown email' from 'wrong password' (no enumeration)."""


@dataclass(frozen=True)
class TokenPair:
    """What a login/refresh yields: a signed access JWT plus the raw opaque
    refresh token to set in the httpOnly cookie."""

    access_token: str
    refresh_token: str
    expires_in: int


_INVALID_CREDENTIALS = "invalid credentials"
_INVALID_REFRESH = "invalid refresh token"
_REUSE_DETECTED = "refresh token reuse detected"


@lru_cache(maxsize=1)
def _timing_equalizer_hash() -> str:
    """A throwaway bcrypt hash verified against when a user is absent/inactive,
    so login latency does not reveal whether an email exists."""
    return hash_password("timing-equalizer-not-a-real-password")


async def authenticate_user(settings: Settings, email: str, password: str) -> UserRecord:
    """Return the user for valid credentials, else raise a uniform ``AuthError``."""
    async with connect(settings.database_url) as conn:
        user = await get_user_by_email(conn, email)

    if user is None or not user.is_active:
        # Burn comparable time so timing does not leak account existence.
        verify_password(password, _timing_equalizer_hash())
        raise AuthError(_INVALID_CREDENTIALS)

    if not verify_password(password, user.password_hash):
        raise AuthError(_INVALID_CREDENTIALS)

    return user


def _mint_access_token(settings: Settings, user: UserRecord) -> str:
    return encode_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        secret=settings.jwt_secret,
        expiry_seconds=settings.jwt_access_expiry_seconds,
    )


async def issue_token_pair(settings: Settings, user: UserRecord) -> TokenPair:
    """Start a new refresh-token family for a freshly authenticated user."""
    raw_refresh = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expiry_days)
    async with connect(settings.database_url) as conn, conn.transaction():
        await insert_refresh_token(
            conn,
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_hash=hash_refresh_token(raw_refresh),
            family_id=uuid.uuid4(),
            expires_at=expires_at,
        )
        await touch_last_login(conn, user.id)
    return TokenPair(
        access_token=_mint_access_token(settings, user),
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_expiry_seconds,
    )


async def login(settings: Settings, email: str, password: str) -> TokenPair:
    """Authenticate credentials and issue a fresh access/refresh pair."""
    user = await authenticate_user(settings, email, password)
    return await issue_token_pair(settings, user)


async def rotate_refresh_token(settings: Settings, raw_refresh: str) -> TokenPair:
    """Rotate a refresh token, detecting and punishing reuse of a spent token."""
    token_hash = hash_refresh_token(raw_refresh)
    now = datetime.now(UTC)

    async with connect(settings.database_url) as conn:
        record = await get_refresh_token_by_hash(conn, token_hash)

        if record is None or record.status == "revoked" or record.expires_at <= now:
            raise AuthError(_INVALID_REFRESH)

        if record.status == "rotated":
            # Replay of an already-spent token: revoke the whole family, then reject.
            async with conn.transaction():
                await revoke_family(conn, record.family_id)
            raise AuthError(_REUSE_DETECTED)

        # status == 'active': the user must still exist and be active.
        user = await get_user_by_id(conn, record.user_id)
        if user is None or not user.is_active:
            async with conn.transaction():
                await revoke_family(conn, record.family_id)
            raise AuthError(_INVALID_REFRESH)

        new_raw = generate_refresh_token()
        new_expires = now + timedelta(days=settings.jwt_refresh_expiry_days)
        raced = False
        async with conn.transaction():
            claimed = await mark_rotated(conn, record.id)
            if claimed == 0:
                # Lost a concurrent rotation: the token was spent between our read
                # and now. Same response as an explicit replay — burn the family.
                await revoke_family(conn, record.family_id)
                raced = True
            else:
                await insert_refresh_token(
                    conn,
                    user_id=record.user_id,
                    tenant_id=record.tenant_id,
                    token_hash=hash_refresh_token(new_raw),
                    family_id=record.family_id,
                    parent_id=record.id,
                    expires_at=new_expires,
                )
        if raced:
            raise AuthError(_REUSE_DETECTED)

    return TokenPair(
        access_token=_mint_access_token(settings, user),
        refresh_token=new_raw,
        expires_in=settings.jwt_access_expiry_seconds,
    )


async def revoke_refresh_token(settings: Settings, raw_refresh: str) -> None:
    """Revoke the whole family for a refresh token (logout). Idempotent."""
    token_hash = hash_refresh_token(raw_refresh)
    async with connect(settings.database_url) as conn:
        record = await get_refresh_token_by_hash(conn, token_hash)
        if record is None:
            return
        async with conn.transaction():
            await revoke_family(conn, record.family_id)
