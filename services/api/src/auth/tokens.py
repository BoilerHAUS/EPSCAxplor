"""Access tokens (signed JWTs) and refresh tokens (opaque, server-tracked).

Access tokens are short-lived JWTs decoded on every request. Refresh tokens are
NOT JWTs: they are high-entropy opaque strings whose SHA-256 hash is stored in
the ``refresh_tokens`` table, so they can be revoked and rotated server-side
(a self-verifying JWT refresh token could not be revoked before its expiry).
"""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid

from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

# HS256 is pinned everywhere: never trust the token's own ``alg`` header, which is
# how ``alg=none`` and HS/RS confusion attacks slip through.
ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 — a token-type label, not a secret

# 48 bytes -> ~64 url-safe chars (384 bits of entropy).
REFRESH_TOKEN_BYTES = 48


class TokenError(Exception):
    """Raised when an access token is missing, malformed, expired, or forged."""


class AccessClaims(BaseModel):
    """Decoded and validated access-token payload."""

    sub: uuid.UUID  # user id
    tenant_id: uuid.UUID
    role: str
    type: str
    jti: str
    iat: int
    exp: int


def encode_access_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    secret: str,
    expiry_seconds: int,
) -> str:
    """Sign a short-lived access JWT carrying the tenant/user context."""
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + expiry_seconds,
    }
    encoded: str = jwt.encode(claims, secret, algorithm=ALGORITHM)
    return encoded


def decode_access_token(token: str, secret: str) -> AccessClaims:
    """Verify and decode an access JWT into typed claims.

    Raises ``TokenError`` on any failure (bad signature, expiry, wrong
    algorithm, wrong token type, or malformed claims) — callers should map that
    to a single ``401 unauthorized`` with no detail about which check failed.
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError("invalid or expired access token") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("not an access token")

    try:
        return AccessClaims.model_validate(payload)
    except ValidationError as exc:
        raise TokenError("malformed access-token claims") from exc


def generate_refresh_token() -> str:
    """Return a fresh, high-entropy, url-safe opaque refresh token."""
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(raw: str) -> str:
    """Return the SHA-256 hex digest stored for a raw refresh token.

    A fast hash is appropriate (unlike passwords) because the input is already
    high-entropy random, and equality lookups by hash must be indexable.
    """
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
