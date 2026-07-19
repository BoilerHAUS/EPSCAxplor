"""Trust-boundary tests for ``_client_key`` (#140).

Traefik *appends* the true socket peer as the right-most ``X-Forwarded-For``
entry, so the per-IP limiter key must be taken from the right (Nth-from-right =
``trusted_proxy_hops``). A client-supplied *leading* XFF value is attacker
controlled and must never influence the key.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.auth.dependencies import _client_key


@dataclass
class _FakeClient:
    host: str


class _FakeRequest:
    """Minimal stand-in exposing the two attributes ``_client_key`` reads."""

    def __init__(self, *, xff: str | None = None, peer: str | None = None) -> None:
        self.headers: dict[str, str] = {} if xff is None else {"x-forwarded-for": xff}
        self.client = _FakeClient(peer) if peer is not None else None


def _key(*, xff: str | None = None, peer: str | None = None, hops: int = 1) -> str:
    return _client_key(_FakeRequest(xff=xff, peer=peer), hops)  # type: ignore[arg-type]


def test_no_xff_uses_peer_ip() -> None:
    assert _key(peer="9.9.9.9", hops=1) == "9.9.9.9"


def test_no_xff_no_client_returns_unknown() -> None:
    assert _key(peer=None, hops=1) == "unknown"


def test_single_hop_takes_rightmost_entry() -> None:
    # One proxy hop: Traefik appended the real peer as the sole entry.
    assert _key(xff="1.1.1.1", peer="10.0.0.5", hops=1) == "1.1.1.1"


def test_spoofed_leading_entry_ignored() -> None:
    # Attacker prepended 6.6.6.6; Traefik appended the real peer 1.1.1.1.
    assert _key(xff="6.6.6.6, 1.1.1.1", peer="10.0.0.5", hops=1) == "1.1.1.1"


def test_two_hops_takes_second_from_right() -> None:
    assert _key(xff="a, b, c", hops=2) == "b"


def test_fewer_entries_than_hops_falls_back_to_peer() -> None:
    # Expected two trusted hops but only one entry: the request did not traverse
    # the trusted proxy chain — trust nothing from XFF.
    assert _key(xff="1.1.1.1", peer="9.9.9.9", hops=2) == "9.9.9.9"


def test_hops_zero_ignores_xff_uses_peer() -> None:
    # Direct-peer mode (no proxy in front, e.g. local/dev).
    assert _key(xff="1.1.1.1", peer="9.9.9.9", hops=0) == "9.9.9.9"


def test_whitespace_and_empty_entries_are_normalized() -> None:
    assert _key(xff=" 6.6.6.6 ,, 1.1.1.1 , ", hops=1) == "1.1.1.1"


def test_ipv6_entry_preserved() -> None:
    # Split on commas only — never on the colons inside an IPv6 address.
    assert _key(xff="::1, 2001:db8::1", hops=1) == "2001:db8::1"
