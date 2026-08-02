-- Migration 011: Stripe subscription sync columns (#32)
--
-- Migration 003 created `subscriptions` with `stripe_customer_id` and
-- `stripe_subscription_id` already in place, so the Stripe integration needs no
-- rename/backfill — only the additive columns below, plus the conflict target
-- the webhook upsert needs.
--
-- All four columns are nullable (or defaulted), and the unique index is partial,
-- so this migration is safe to apply to a populated `subscriptions` table and
-- changes the behaviour of no existing query.  Migrations are applied MANUALLY
-- in sorted order; prod deploys do NOT run them (see CLAUDE.md).  Apply with
-- `psql -v ON_ERROR_STOP=1` so a failure is visible to the operator.
--
-- ─── stripe_price_id ─────────────────────────────────────────────────────────
-- The Stripe Price the subscription is billed on.  This is the SERVER-SIDE
-- source of truth for `tier`: the webhook maps price_id -> tier through the
-- configured catalog (src/billing/plans.py) and never accepts a client-supplied
-- tier.  Storing it makes that derivation auditable after the fact and lets a
-- price change be detected on `customer.subscription.updated`.
--
-- ─── stripe_status ───────────────────────────────────────────────────────────
-- The RAW Stripe subscription status, stored verbatim alongside the mapped
-- `status`.  Necessary because the two vocabularies do not line up:
--
--   * Stripe spells it `canceled` (one L); 003's CHECK requires `cancelled`.
--   * Stripe has statuses 003's CHECK has no member for — `incomplete`,
--     `incomplete_expired`, `unpaid`, `paused`.
--
-- Rather than widen 003's CHECK (which would let a typo through and would make
-- `cancelled`/`canceled` both legal forever), the app maps Stripe -> the
-- existing four-value domain and keeps the original here.  Nothing is lost, the
-- mapping can be revised in code without another migration, and every existing
-- row and reader of `status` is untouched.
--
-- ─── cancel_at_period_end ────────────────────────────────────────────────────
-- True once the customer cancels via the Billing Portal.  Distinct from
-- `status`: such a subscription stays `active` and fully entitled until the
-- period actually ends, so this is a UI/renewal signal, NOT an entitlement one.
-- NOT NULL DEFAULT FALSE backfills existing rows correctly — a row that predates
-- Stripe sync was never set to cancel.
--
-- ─── stripe_event_created_at ─────────────────────────────────────────────────
-- The `created` timestamp of the webhook event that last wrote this row.
-- Stripe delivers events AT LEAST ONCE and IN NO GUARANTEED ORDER, so a stale
-- `customer.subscription.updated` can arrive after a newer one and would
-- otherwise overwrite current state with old state (e.g. re-applying a downgrade
-- on top of an upgrade).  The upsert compares this column and refuses to move
-- backwards.  The idempotency table (012) stops exact REPLAYS; this column stops
-- REORDERING.  They are different failure modes and both are needed.
--
-- NULL means "written before this guard existed" and always loses to an incoming
-- event, so no manual backfill is required.

ALTER TABLE subscriptions
    ADD COLUMN IF NOT EXISTS stripe_price_id         TEXT,
    ADD COLUMN IF NOT EXISTS stripe_status           TEXT,
    ADD COLUMN IF NOT EXISTS cancel_at_period_end    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS stripe_event_created_at TIMESTAMPTZ;

-- Conflict target for the webhook upsert, and the invariant that one Stripe
-- subscription maps to exactly one row.
--
-- PARTIAL (`WHERE ... IS NOT NULL`) is load-bearing, for two independent reasons:
--
--  1. Enterprise is deliberately NOT self-serve (#35) — those rows are
--     provisioned by hand with a NULL `stripe_subscription_id`.  A plain UNIQUE
--     constraint would technically permit several NULLs (SQL treats NULLs as
--     distinct), but a partial index states the intent and keeps those rows out
--     of the index entirely.
--  2. It is the index the upsert INFERS.  `ON CONFLICT (stripe_subscription_id)
--     WHERE stripe_subscription_id IS NOT NULL` matches this predicate exactly;
--     the predicate must stay in sync with the one in src/db/subscriptions.py or
--     the upsert fails at runtime with "no unique or exclusion constraint
--     matching the ON CONFLICT specification".
--
-- Deliberately NOT unique on `tenant_id`: a tenant that cancels and later
-- re-subscribes legitimately owns more than one row, and
-- `get_tenant_subscription` already resolves that by taking the newest.

CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription_id
    ON subscriptions (stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;

-- Supports resolving a webhook back to its tenant when the event carries only a
-- customer id (the `invoice.*` events do).  Not unique: one Stripe Customer can
-- accumulate several subscription rows over time.
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer_id
    ON subscriptions (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;
