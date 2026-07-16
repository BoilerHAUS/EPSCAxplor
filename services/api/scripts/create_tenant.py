"""Create a tenant, optionally with a starting subscription (#31 setup).

Tenants are otherwise only created by migration 008 (the bootstrap ``system``
tenant), so multi-tenant verification and early white-label onboarding need a
way to mint them out-of-band. Run from ``services/api`` (so ``src`` imports
resolve), against the DB through the socat tunnel documented in CLAUDE.md, or
inside the deployed API image with its own ``DATABASE_URL``:

    DATABASE_URL="postgresql://epsca_user:...@127.0.0.1:5433/epsca?sslmode=disable" \\
      python -m scripts.create_tenant --name "Tenant A" --slug tenant-a --tier professional

Pass ``--query-limit-monthly`` (and/or ``--user-limit``) to attach an active
subscription in the same step — e.g. a low quota to exercise the 429 tier limit:

    python -m scripts.create_tenant --name "Rate Test" --slug rate-test \\
      --tier professional --query-limit-monthly 3

Create the tenant's first user afterwards with ``scripts.create_user``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid

from src.db import connect

TIERS = ("individual", "professional", "enterprise")


def _resolve_database_url(arg: str | None) -> str:
    url = arg or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not url:
        raise SystemExit("Provide --database-url or set DATABASE_URL / POSTGRES_DSN.")
    return url


async def _create_tenant(
    *,
    name: str,
    slug: str,
    tier: str,
    query_limit_monthly: int | None,
    user_limit: int | None,
    database_url: str,
) -> tuple[uuid.UUID, bool]:
    """Insert the tenant (and an active subscription when a limit is given).

    Returns ``(tenant_id, subscription_created)``.
    """
    async with connect(database_url) as conn:
        existing = await conn.fetchval("SELECT id FROM tenants WHERE slug = $1", slug)
        if existing is not None:
            raise SystemExit(f"A tenant with slug {slug!r} already exists.")
        tenant_id: uuid.UUID = await conn.fetchval(
            "INSERT INTO tenants (name, slug, tier) VALUES ($1, $2, $3) RETURNING id",
            name,
            slug,
            tier,
        )
        subscription_created = query_limit_monthly is not None or user_limit is not None
        if subscription_created:
            # The subscription tier mirrors the tenant tier; the billing period is
            # left NULL so the limiter falls back to the current calendar month.
            await conn.execute(
                "INSERT INTO subscriptions "
                "(tenant_id, tier, status, query_limit_monthly, user_limit) "
                "VALUES ($1, $2, 'active', $3, $4)",
                tenant_id,
                tier,
                query_limit_monthly,
                user_limit,
            )
    return tenant_id, subscription_created


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an EPSCAxplor tenant.")
    parser.add_argument("--name", required=True, help="Human-readable tenant name.")
    parser.add_argument("--slug", required=True, help="URL-safe unique identifier.")
    parser.add_argument("--tier", required=True, choices=TIERS)
    parser.add_argument(
        "--query-limit-monthly",
        type=int,
        default=None,
        help="Attach an active subscription with this monthly query quota.",
    )
    parser.add_argument(
        "--user-limit",
        type=int,
        default=None,
        help="Attach an active subscription with this user limit.",
    )
    parser.add_argument("--database-url", default=None, help="Overrides DATABASE_URL/POSTGRES_DSN.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    database_url = _resolve_database_url(args.database_url)
    tenant_id, subscription_created = asyncio.run(
        _create_tenant(
            name=args.name,
            slug=args.slug,
            tier=args.tier,
            query_limit_monthly=args.query_limit_monthly,
            user_limit=args.user_limit,
            database_url=database_url,
        )
    )
    print(f"Created tenant {args.slug!r} ({tenant_id}) on the {args.tier} tier.")
    if subscription_created:
        print(
            "  Attached subscription: "
            f"query_limit_monthly={args.query_limit_monthly}, user_limit={args.user_limit}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
