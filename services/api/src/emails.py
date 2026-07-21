"""Email normalization for login + uniqueness (#141).

Folding case (and trimming surrounding whitespace) makes login case-insensitive
and lets a single ``LOWER(email)`` unique index reject accounts that differ only
by case: ``You@x.com`` and ``you@x.com`` normalize to the same value.

Kept deliberately dependency-free (stdlib only) so both the data-access layer
(``src.db.users``) and the operator CLI (``scripts.create_user``) can import it
without pulling in ``src.auth`` — importing anything under ``src.auth`` would
trigger that package's eager ``__init__`` and risk an import cycle.
"""

from __future__ import annotations


def normalize_email(email: str) -> str:
    """Return the canonical form used for storage and lookup: trimmed, lowercased.

    Idempotent — normalizing an already-normalized value returns it unchanged.
    Local-part-preserving: only case and surrounding whitespace are folded; dots
    and plus-addressing are left intact (no provider-specific canonicalization).

    ASCII-oriented: Python ``str.lower()`` and Postgres ``LOWER()`` (used by the
    ``idx_users_email_lower`` unique index) can disagree on non-ASCII case-folding,
    so the write ingress (scripts/create_user.py) rejects non-ASCII input to keep
    the app-side lookup consistent with the DB-side index.
    """
    return email.strip().lower()
