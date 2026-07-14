"""Auth package.

Real JWT authentication with refresh-token rotation (#23), replacing the interim
shared-token stub from #85. The public surface is re-exported here so callers can
``from src.auth import ...`` without depending on submodule layout:

- ``CurrentUser`` / ``get_current_user`` — request auth (``dependencies`` module)
- ``enforce_rate_limit`` — interim per-client limiter (``dependencies`` module)

Login/refresh/logout orchestration lives in ``src.auth.service``; the token and
password primitives in ``src.auth.tokens`` / ``src.auth.passwords``.
"""

from __future__ import annotations

from src.auth.dependencies import CurrentUser, enforce_rate_limit, get_current_user

__all__ = ["CurrentUser", "enforce_rate_limit", "get_current_user"]
