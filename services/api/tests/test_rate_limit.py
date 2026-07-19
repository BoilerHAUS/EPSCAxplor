"""Unit tests for ``SlidingWindowLimiter`` (#140).

Pure, clock-injected sliding-window limiter with bounded memory. The FastAPI
dependencies (``enforce_rate_limit`` / ``enforce_auth_rate_limit``) are thin
wrappers over this; behaviour is exercised here in isolation.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from src.auth.rate_limit import SlidingWindowLimiter
from src.config import Settings

WINDOW = 60.0
BIG = 10_000  # max_keys high enough that eviction never triggers


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = dict(
        database_url="postgresql://user:pass@localhost/epsca",
        qdrant_url="http://localhost:6333",
        ollama_url="http://localhost:11434",
        anthropic_api_key="test-key",
        jwt_secret="rate-limit-test-secret",
    )
    base.update(overrides)
    return Settings(**base)


def _limiter() -> SlidingWindowLimiter:
    return SlidingWindowLimiter(window_seconds=WINDOW)


def test_under_limit_allows() -> None:
    lim = _limiter()
    assert all(lim.check("k", limit=3, now=t, max_keys=BIG) for t in (0.0, 1.0, 2.0))


def test_at_limit_rejects() -> None:
    lim = _limiter()
    for t in (0.0, 1.0, 2.0):
        assert lim.check("k", limit=3, now=t, max_keys=BIG) is True
    assert lim.check("k", limit=3, now=3.0, max_keys=BIG) is False


def test_window_expiry_frees_slots() -> None:
    lim = _limiter()
    assert lim.check("k", limit=1, now=1000.0, max_keys=BIG) is True
    assert lim.check("k", limit=1, now=1000.5, max_keys=BIG) is False
    # Advance past the window: the old timestamp ages out and a slot frees up.
    assert lim.check("k", limit=1, now=1061.0, max_keys=BIG) is True


def test_separate_keys_independent() -> None:
    lim = _limiter()
    assert lim.check("a", limit=1, now=0.0, max_keys=BIG) is True
    assert lim.check("a", limit=1, now=0.1, max_keys=BIG) is False
    # Key "b" has its own window, unaffected by "a" being exhausted.
    assert lim.check("b", limit=1, now=0.2, max_keys=BIG) is True


def test_disabled_when_limit_zero() -> None:
    lim = _limiter()
    for t in range(50):
        assert lim.check("k", limit=0, now=float(t), max_keys=BIG) is True
    # Disabled limiter must not accumulate any per-key state.
    assert len(lim._buckets) == 0


def test_empty_deque_key_is_evicted_under_pressure() -> None:
    lim = _limiter()
    max_keys = 100
    # Fill exactly max_keys distinct keys within the window at t=0.
    for i in range(max_keys):
        assert lim.check(f"k{i}", limit=5, now=0.0, max_keys=max_keys) is True
    assert len(lim._buckets) == max_keys
    # Advance well past the window so every existing key is now idle, then add
    # one fresh key. The sweep must reclaim the fully-expired (idle) buckets.
    assert lim.check("fresh", limit=5, now=1000.0, max_keys=max_keys) is True
    assert len(lim._buckets) <= max_keys
    assert "fresh" in lim._buckets
    assert "k0" not in lim._buckets  # an idle key was evicted


def test_key_flood_respects_max_keys() -> None:
    lim = _limiter()
    max_keys = 100
    # Flood with many distinct active keys inside one window.
    for i in range(max_keys + 500):
        lim.check(f"flood{i}", limit=5, now=0.0, max_keys=max_keys)
    assert len(lim._buckets) <= max_keys
    # Most-recently-seen keys survive; the oldest were evicted.
    assert f"flood{max_keys + 499}" in lim._buckets


def test_reject_does_not_extend_window() -> None:
    lim = _limiter()
    # One allowed hit at t=0; repeated rejects must not push the expiry forward.
    assert lim.check("k", limit=1, now=0.0, max_keys=BIG) is True
    for t in (10.0, 20.0, 30.0, 50.0):
        assert lim.check("k", limit=1, now=t, max_keys=BIG) is False
    # The single recorded hit (t=0) ages out at t>60 regardless of the rejects.
    assert lim.check("k", limit=1, now=61.0, max_keys=BIG) is True


# ─── settings validation (#140) ─────────────────────────────────────────────


def test_defaults_are_sane() -> None:
    s = _settings()
    assert s.query_rate_limit_per_minute == 30
    assert s.auth_rate_limit_per_minute == 10
    assert s.trusted_proxy_hops == 1
    assert s.rate_limit_max_keys == 10_000


@pytest.mark.parametrize(
    "field",
    ["query_rate_limit_per_minute", "auth_rate_limit_per_minute", "trusted_proxy_hops"],
)
def test_negative_rate_settings_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        _settings(**{field: -1})


def test_zero_max_keys_rejected() -> None:
    # 0 would force an eviction sweep on every check(); must be >= 1.
    with pytest.raises(ValidationError):
        _settings(rate_limit_max_keys=0)
