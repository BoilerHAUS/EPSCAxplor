"""Tests for src/auth/tokens.py — JWT access tokens + opaque refresh tokens (#23)."""

from __future__ import annotations

import base64
import json
import string
import time
import uuid

import pytest
from jose import jwt

from src.auth.tokens import (
    ALGORITHM,
    AccessClaims,
    TokenError,
    decode_access_token,
    encode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)

SECRET = "unit-test-secret"  # noqa: S105
USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _encode(expiry_seconds: int = 900) -> str:
    return encode_access_token(
        user_id=USER_ID,
        tenant_id=TENANT_ID,
        role="owner",
        secret=SECRET,
        expiry_seconds=expiry_seconds,
    )


def test_round_trip_returns_claims() -> None:
    claims = decode_access_token(_encode(), SECRET)
    assert isinstance(claims, AccessClaims)
    assert claims.sub == USER_ID
    assert claims.tenant_id == TENANT_ID
    assert claims.role == "owner"
    assert claims.type == "access"
    assert claims.jti
    assert claims.exp > claims.iat


def test_expired_token_raises() -> None:
    with pytest.raises(TokenError):
        decode_access_token(_encode(expiry_seconds=-1), SECRET)


def test_wrong_secret_raises() -> None:
    with pytest.raises(TokenError):
        decode_access_token(_encode(), "a-different-secret")


def test_tampered_token_raises() -> None:
    head, payload, sig = _encode().split(".")
    with pytest.raises(TokenError):
        decode_access_token(f"{head}.{payload}x.{sig}", SECRET)


def test_alg_none_token_rejected() -> None:
    # Classic JWT footgun: an attacker strips the signature and sets alg=none.
    # jose refuses to *encode* one, so hand-craft the unsigned token.
    def _seg(obj: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    header = _seg({"alg": "none", "typ": "JWT"})
    payload = _seg(
        {
            "sub": str(USER_ID),
            "tenant_id": str(TENANT_ID),
            "role": "owner",
            "type": "access",
            "jti": "x",
            "iat": 0,
            "exp": 9999999999,
        }
    )
    forged = f"{header}.{payload}."
    with pytest.raises(TokenError):
        decode_access_token(forged, SECRET)


def test_non_access_token_type_rejected() -> None:
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(USER_ID),
            "tenant_id": str(TENANT_ID),
            "role": "owner",
            "type": "refresh",
            "jti": "x",
            "iat": now,
            "exp": now + 900,
        },
        SECRET,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenError):
        decode_access_token(token, SECRET)


def test_generate_refresh_token_is_unique_and_urlsafe() -> None:
    a = generate_refresh_token()
    b = generate_refresh_token()
    assert a != b
    assert len(a) >= 43  # token_urlsafe(48) yields ~64 chars
    allowed = set(string.ascii_letters + string.digits + "-_")
    assert set(a) <= allowed


def test_hash_refresh_token_is_deterministic_sha256_hex() -> None:
    h = hash_refresh_token("some-token")
    assert h == hash_refresh_token("some-token")
    assert h != "some-token"
    assert len(h) == 64
    int(h, 16)  # parses as hex
