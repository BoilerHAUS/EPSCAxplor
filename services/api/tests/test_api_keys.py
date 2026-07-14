"""Tests for src/auth/api_keys.py — API key generation/hashing (#24)."""

from __future__ import annotations

import string

from src.auth.api_keys import (
    API_KEY_PREFIX,
    generate_api_key,
    hash_api_key,
    looks_like_api_key,
)


def test_generate_has_prefix_and_entropy() -> None:
    key = generate_api_key()
    assert key.startswith(API_KEY_PREFIX)
    body = key[len(API_KEY_PREFIX) :]
    assert len(body) >= 43  # token_urlsafe(32) yields ~43 chars
    allowed = set(string.ascii_letters + string.digits + "-_")
    assert set(body) <= allowed


def test_generate_is_unique() -> None:
    assert generate_api_key() != generate_api_key()


def test_hash_is_deterministic_sha256_hex() -> None:
    key = generate_api_key()
    h = hash_api_key(key)
    assert h == hash_api_key(key)
    assert len(h) == 64
    int(h, 16)  # parses as hex
    assert h != key


def test_looks_like_api_key_by_prefix() -> None:
    assert looks_like_api_key(generate_api_key()) is True
    assert looks_like_api_key("eyJhbGciOiJIUzI1NiJ9.payload.sig") is False
    assert looks_like_api_key("") is False
