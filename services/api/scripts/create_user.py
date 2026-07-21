"""Create a user (with a bcrypt-hashed password) for an existing tenant.

Registration is intentionally not a Phase 3 API endpoint, so the bootstrap admin
and any early beta users are created with this operator CLI. Run it against the
VPS Postgres — for the deployed DB, through the socat tunnel documented in
CLAUDE.md — after migration 008 has seeded the ``system`` tenant.

Run from ``services/api`` so ``src`` is importable:

    DATABASE_URL="postgresql://epsca_user:...@127.0.0.1:5433/epsca?sslmode=disable" \\
      python -m scripts.create_user --tenant-slug system --email you@example.com --role owner

The password is read interactively (never a CLI argument), so it does not leak
into shell history or process listings.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
import uuid

from src.auth.passwords import hash_password
from src.db import connect
from src.db.subscriptions import get_tenant_subscription
from src.db.users import count_users_for_tenant
from src.emails import normalize_email

DEFAULT_ROUNDS = 12
ROLES = ("owner", "admin", "member")


def _resolve_database_url(arg: str | None) -> str:
    url = arg or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not url:
        raise SystemExit("Provide --database-url or set DATABASE_URL / POSTGRES_DSN.")
    return url


async def _create_user(
    *,
    tenant_slug: str,
    email: str,
    role: str,
    password: str,
    rounds: int,
    database_url: str,
) -> uuid.UUID:
    """Insert a user under the tenant identified by slug; return the new id."""
    # Store the canonical (lowercased) email so the LOWER(email) unique index
    # holds and the account is reachable by any casing at login (#141). Reject
    # empty/malformed or non-ASCII input at this ingress: it is the only path that
    # writes emails, and Python str.lower() and Postgres LOWER() can diverge on
    # non-ASCII, which would desync the app's lookup from the functional index.
    email = normalize_email(email)
    if "@" not in email or not email.isascii():
        raise SystemExit(
            "Email must be a non-empty ASCII address containing '@' "
            "(non-ASCII emails are not supported)."
        )
    password_hash = hash_password(password, rounds=rounds)
    async with connect(database_url) as conn:
        tenant_id = await conn.fetchval("SELECT id FROM tenants WHERE slug = $1", tenant_slug)
        if tenant_id is None:
            raise SystemExit(f"No tenant with slug {tenant_slug!r}; seed it first (migration 008).")
        # Enforce the tenant's user_limit when a subscription sets one (fail-open otherwise).
        sub = await get_tenant_subscription(conn, tenant_id)
        if sub is not None and sub.user_limit is not None:
            existing = await count_users_for_tenant(conn, tenant_id)
            if existing >= sub.user_limit:
                raise SystemExit(
                    f"Tenant {tenant_slug!r} is at its user limit ({sub.user_limit}); "
                    "upgrade the subscription tier to add more users."
                )
        row = await conn.fetchrow(
            "INSERT INTO users (tenant_id, email, password_hash, role) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            tenant_id,
            email,
            password_hash,
            role,
        )
        new_id: uuid.UUID = row["id"]
        return new_id


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an EPSCAxplor user.")
    parser.add_argument("--tenant-slug", required=True, help="Slug of an existing tenant.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", default="member", choices=ROLES)
    parser.add_argument("--database-url", default=None, help="Overrides DATABASE_URL/POSTGRES_DSN.")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="bcrypt cost factor.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    database_url = _resolve_database_url(args.database_url)

    password = getpass.getpass("Password: ")
    if not password:
        print("Password must not be empty.", file=sys.stderr)
        return 1
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1

    user_id = asyncio.run(
        _create_user(
            tenant_slug=args.tenant_slug,
            email=args.email,
            role=args.role,
            password=password,
            rounds=args.rounds,
            database_url=database_url,
        )
    )
    stored_email = normalize_email(args.email)
    print(f"Created user {stored_email} ({user_id}) in tenant {args.tenant_slug!r} as {args.role}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
