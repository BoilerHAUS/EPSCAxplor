"""Auth package.

Real JWT authentication with refresh-token rotation (#23), replacing the interim
shared-token stub from #85. The public surface is re-exported here so callers can
``from src.auth import ...`` without depending on submodule layout:

- ``CurrentUser`` / ``get_current_user`` — request auth (``dependencies`` module)
- ``enforce_rate_limit`` / ``enforce_auth_rate_limit`` — per-client limiters
  (``dependencies`` module)

Login/refresh/logout orchestration lives in ``src.auth.service``; the token and
password primitives in ``src.auth.tokens`` / ``src.auth.passwords``.
"""

from __future__ import annotations

from src.auth.dependencies import (
    CurrentUser,
    enforce_auth_rate_limit,
    enforce_rate_limit,
    get_current_user,
)
from src.auth.tier_limit import enforce_tier_limit

__all__ = [
    "CurrentUser",
    "enforce_auth_rate_limit",
    "enforce_rate_limit",
    "enforce_tier_limit",
    "get_current_user",
]
