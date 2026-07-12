"""Password hashing via bcrypt.

bcrypt is used directly rather than through passlib: passlib 1.7.4 (the last
release, from 2020) reads ``bcrypt.__about__.__version__``, which was removed in
bcrypt 4.1, so the combination raises spurious errors on modern bcrypt. The
bcrypt library's own API is small and stable, so we depend on it directly.
"""

from __future__ import annotations

import bcrypt

# bcrypt only hashes the first 72 bytes of the input. Silent truncation would let
# two distinct long passwords collide, so we reject over-length inputs at hash
# time instead. Verification treats them as a non-match (never raises).
BCRYPT_MAX_BYTES = 72

# Sensible default work factor; callers pass settings.bcrypt_rounds explicitly.
DEFAULT_ROUNDS = 12


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds bcrypt's 72-byte hard limit."""


def _encode_within_limit(raw: str) -> bytes:
    encoded = raw.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise PasswordTooLongError(
            f"Password exceeds bcrypt's {BCRYPT_MAX_BYTES}-byte limit."
        )
    return encoded


def hash_password(raw: str, *, rounds: int = DEFAULT_ROUNDS) -> str:
    """Return a bcrypt hash (salt embedded) for a plaintext password.

    Raises ``PasswordTooLongError`` if the UTF-8 encoding exceeds 72 bytes.
    """
    encoded = _encode_within_limit(raw)
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    """Constant-time check of a plaintext password against a bcrypt hash.

    Returns ``False`` (never raises) for an over-length password or a malformed
    stored hash, so callers can treat any failure as a plain auth denial.
    """
    try:
        encoded = _encode_within_limit(raw)
    except PasswordTooLongError:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError:
        # Malformed/unsupported hash string — treat as a non-match, not a crash.
        return False
