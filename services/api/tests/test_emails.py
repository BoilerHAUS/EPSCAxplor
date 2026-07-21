"""Tests for src/emails.py — email normalization for login + uniqueness (#141)."""

from __future__ import annotations

import pytest

from src.emails import normalize_email


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("You@X.com", "you@x.com"),
        ("MixedCase@Example.ORG", "mixedcase@example.org"),
        ("already@lower.com", "already@lower.com"),
        ("  padded@spaces.io  ", "padded@spaces.io"),
        ("\tTabbed@Domain.Com\n", "tabbed@domain.com"),
    ],
)
def test_normalize_lowercases_and_strips(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


def test_normalize_is_idempotent() -> None:
    once = normalize_email("  You@X.com ")
    assert normalize_email(once) == once


def test_case_only_difference_collapses_to_same_value() -> None:
    assert normalize_email("You@x.com") == normalize_email("you@X.COM")


def test_whitespace_only_collapses_to_empty() -> None:
    # Pure normalizer: it does not raise. Callers guard the empty result — the API
    # via LoginRequest's post-normalize length check, the CLI via its ingress guard.
    assert normalize_email("   ") == ""


def test_non_ascii_is_not_ascii_folded() -> None:
    # normalize_email only case-folds; it does not transliterate. Non-ASCII input
    # stays non-ASCII (Python str.lower() != Postgres LOWER() for such chars),
    # which is why scripts/create_user.py rejects non-ASCII at the write ingress.
    assert not normalize_email("İ@X.com").isascii()
