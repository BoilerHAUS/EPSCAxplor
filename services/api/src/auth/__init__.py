"""Auth module — Phase 1 stub.

Provides a get_current_user FastAPI dependency that accepts all requests
without JWT validation.  Auth enforcement is added in a later phase.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

# Hardcoded system tenant UUID used for query logging until real auth is active.
# Must be seeded in the tenants table before query_logs writes succeed.
SYSTEM_TENANT_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class CurrentUser(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None


async def get_current_user() -> CurrentUser:
    """Stub dependency — returns the system tenant with no user."""
    return CurrentUser(tenant_id=SYSTEM_TENANT_ID)
