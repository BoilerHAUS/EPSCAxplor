"""API key generation and hashing for enterprise-tier auth (#24).

An API key is presented as ``Authorization: Bearer <key>``, the same header as a
JWT. Its distinct prefix lets ``get_current_user`` route it to API-key auth vs.
JWT decode. Only the SHA-256 hash of the key is stored (never plaintext),
mirroring refresh tokens.
"""

from __future__ import annotations

import hashlib
import secrets

# Public identifier prefix (à la Stripe's sk_) — not itself a secret.
API_KEY_PREFIX = "epsca_sk_"  # noqa: S105
_API_KEY_BYTES = 32


def generate_api_key() -> str:
    """Return a new raw API key: the prefix plus high-entropy random."""
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(_API_KEY_BYTES)}"


def hash_api_key(raw: str) -> str:
    """Return the SHA-256 hex digest stored for a raw API key."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def looks_like_api_key(token: str) -> bool:
    """True when a bearer token is an API key (vs a JWT), by its prefix."""
    return token.startswith(API_KEY_PREFIX)
