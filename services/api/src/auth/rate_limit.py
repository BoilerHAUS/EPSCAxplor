"""In-process sliding-window rate limiter with bounded memory (#140).

A single tested primitive backs every per-client limiter in the app: each
guarded surface (``/query``, the auth endpoints) owns its *own* instance, so
their counters are independent. State is in-process, which is sufficient for the
current single-replica deployment; horizontal scaling would need a shared store
(Redis).

The limiter is pure with respect to time — the caller passes ``now`` — so it is
trivially unit-testable and the FastAPI dependencies stay the only place that
reads the clock. Memory is bounded: a key's window is pruned on access, and when
the number of distinct keys exceeds ``max_keys`` an eviction sweep reclaims idle
(fully expired) keys first, then the oldest remaining keys.
"""

from __future__ import annotations

from collections import deque


class SlidingWindowLimiter:
    """Per-key sliding-window counter. Not safe for use across threads."""

    def __init__(self, *, window_seconds: float = 60.0) -> None:
        self._window = window_seconds
        # Per-key timestamps (monotonic seconds) within the current window.
        self._buckets: dict[str, deque[float]] = {}

    def check(self, key: str, *, limit: int, now: float, max_keys: int) -> bool:
        """Record a hit for ``key`` and report whether it is within ``limit``.

        Returns ``True`` when the request is allowed (the hit is recorded) and
        ``False`` when the key has already reached ``limit`` within the window
        (the hit is *not* recorded, so rejects never extend the window).
        A ``limit <= 0`` disables the limiter and stores no state.
        """
        if limit <= 0:
            return True

        window = self._buckets.setdefault(key, deque())
        self._prune(window, now)
        if len(window) >= limit:
            return False
        window.append(now)
        self._evict_if_needed(now, max_keys)
        return True

    def _prune(self, window: deque[float], now: float) -> None:
        """Drop timestamps older than the window from the left of ``window``.

        The boundary is inclusive: a hit aged *exactly* ``window_seconds`` is
        still counted (strict ``>``), so the retained window is ``[now - w, now]``.
        Do not relax this to ``>=`` — it would evict on-boundary hits a tick early.
        """
        while window and now - window[0] > self._window:
            window.popleft()

    def _evict_if_needed(self, now: float, max_keys: int) -> None:
        """Bound memory: reclaim idle keys, then the oldest, above ``max_keys``."""
        if len(self._buckets) <= max_keys:
            return
        # Idle keys first: an empty deque, or one whose newest hit has aged out.
        idle = [
            key
            for key, window in self._buckets.items()
            if not window or now - window[-1] > self._window
        ]
        for key in idle:
            del self._buckets[key]
        if len(self._buckets) <= max_keys:
            return
        # Still over cap (active-key flood): evict the least-recently-seen keys.
        oldest = sorted(self._buckets, key=lambda key: self._buckets[key][-1])
        for key in oldest[: len(self._buckets) - max_keys]:
            del self._buckets[key]
