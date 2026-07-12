"""Tests for src/auth/passwords.py — bcrypt password hashing (#23)."""

from __future__ import annotations

import pytest

from src.auth.passwords import PasswordTooLongError, hash_password, verify_password


def test_hash_differs_from_plaintext() -> None:
    h = hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"
    assert h.startswith("$2b$")


def test_verify_accepts_correct_password() -> None:
    h = hash_password("s3kr3t-pw")
    assert verify_password("s3kr3t-pw", h) is True


def test_verify_rejects_wrong_password() -> None:
    h = hash_password("s3kr3t-pw")
    assert verify_password("not-it", h) is False


def test_hashes_are_salted() -> None:
    # Same input hashed twice must differ (random per-hash salt).
    assert hash_password("same-pw") != hash_password("same-pw")


def test_round_trips_unicode() -> None:
    pw = "pässwörd-😀"
    assert verify_password(pw, hash_password(pw)) is True


def test_rounds_are_reflected_in_hash() -> None:
    # bcrypt embeds the cost factor as $2b$NN$
    assert hash_password("x", rounds=10).startswith("$2b$10$")
    assert hash_password("x", rounds=12).startswith("$2b$12$")


def test_hash_rejects_password_over_72_bytes() -> None:
    # bcrypt only considers the first 72 bytes; silently truncating would let
    # distinct long passwords collide, so we reject loudly at hash time.
    with pytest.raises(PasswordTooLongError):
        hash_password("a" * 73)


def test_verify_returns_false_for_over_72_bytes() -> None:
    # A >72-byte password can never match a hash of a <=72-byte password, and
    # verification must never raise.
    h = hash_password("a" * 72)
    assert verify_password("a" * 73, h) is False


def test_verify_returns_false_for_malformed_hash() -> None:
    assert verify_password("whatever", "not-a-bcrypt-hash") is False
