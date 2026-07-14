-- Migration 008: Seed the bootstrap "system" tenant
-- Fixes the previously un-seeded SYSTEM_TENANT_ID that the interim auth stub and
-- the query_logs FK depended on (best-effort log writes silently failed without a
-- real tenant row). Idempotent, so it is safe to re-apply on every deploy.
--
-- The bootstrap admin USER is intentionally NOT seeded here: a real bcrypt hash
-- must never be committed to git. Create it out-of-band once via
-- services/api/scripts/create_user.py --tenant-slug system --role owner.

INSERT INTO tenants (id, name, slug, tier)
VALUES ('00000000-0000-0000-0000-000000000001', 'System', 'system', 'enterprise')
ON CONFLICT (id) DO NOTHING;
