"""Stripe subscription billing (#32).

Three deliberately separate concerns:

- ``plans``   — the price_id <-> tier catalog and each tier's entitlements. Pure,
  config-driven, and the single source of truth for what a tenant is entitled to.
- ``events``  — inbound webhook payload -> subscription state. Pure functions over
  an already signature-verified event.
- ``gateway`` — outbound Stripe calls and the request shaping that precedes them.

Keeping the pure mapping out of the I/O layer is what makes the security-relevant
rules (tier derives from the server-side price catalog; tax stays off until
registration) testable without mocking the Stripe SDK.
"""
