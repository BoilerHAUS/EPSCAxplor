"""Create an API key for an existing tenant (enterprise-tier auth, #24).

The self-service key-management dashboard is Phase 4 (#35), so keys are minted
with this operator CLI until then. Run from ``services/api`` (so ``src`` imports
resolve), against the DB through the socat tunnel documented in CLAUDE.md:

    DATABASE_URL="postgresql://epsca_user:...@127.0.0.1:5433/epsca?sslmode=disable" \\
      python -m scripts.create_api_key --tenant-slug acme --name "Production key"

The raw key is printed ONCE and never stored — only its SHA-256 hash is saved.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid

from src.auth.api_keys import generate_api_key, hash_api_key
from src.db import connect
from src.db.api_keys import insert_api_key


def _resolve_database_url(arg: str | None) -> str:
    url = arg or os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if not url:
        raise SystemExit("Provide --database-url or set DATABASE_URL / POSTGRES_DSN.")
    return url


async def _create_api_key(
    *, tenant_slug: str, name: str, database_url: str
) -> tuple[uuid.UUID, str]:
    """Mint and store a key for the tenant; return (id, raw_key)."""
    raw_key = generate_api_key()
    async with connect(database_url) as conn:
        tenant_id = await conn.fetchval("SELECT id FROM tenants WHERE slug = $1", tenant_slug)
        if tenant_id is None:
            raise SystemExit(f"No tenant with slug {tenant_slug!r}.")
        key_id = await insert_api_key(
            conn, tenant_id=tenant_id, key_hash=hash_api_key(raw_key), name=name
        )
    return key_id, raw_key


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an EPSCAxplor API key.")
    parser.add_argument("--tenant-slug", required=True, help="Slug of an existing tenant.")
    parser.add_argument("--name", required=True, help="Human label for the key.")
    parser.add_argument("--database-url", default=None, help="Overrides DATABASE_URL/POSTGRES_DSN.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    database_url = _resolve_database_url(args.database_url)
    key_id, raw_key = asyncio.run(
        _create_api_key(tenant_slug=args.tenant_slug, name=args.name, database_url=database_url)
    )
    print(f"Created API key {key_id} for tenant {args.tenant_slug!r}.")
    print("Store this key now — it will not be shown again:")
    print(f"  {raw_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
