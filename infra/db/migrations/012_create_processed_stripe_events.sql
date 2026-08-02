-- Migration 012: Stripe webhook idempotency ledger (#32)
--
-- Stripe delivers each webhook event AT LEAST ONCE: it retries on any non-2xx
-- response, on a timeout, and occasionally re-sends an event that WAS processed
-- successfully but whose 200 was lost in transit.  Every handler therefore has to
-- be safe to run twice.  Rather than make each handler independently idempotent,
-- the app claims an event id here first and skips the whole handler if the claim
-- is already taken.
--
-- The claim is an INSERT ... ON CONFLICT DO NOTHING RETURNING event_id:
-- exactly one concurrent delivery gets a row back and does the work; the others
-- get no row and return 200 without touching `subscriptions`.  That is atomic
-- under Postgres' unique-index enforcement, so it holds even when Stripe's
-- retry overlaps the original delivery on a different worker.
--
-- CRITICAL — the claim and the handler MUST share one transaction.  If the claim
-- were committed first and the handler then failed, the event would be marked
-- processed while nothing was written, and Stripe's retry would be skipped by
-- the claim: the subscription change would be lost permanently.  Rolling both
-- back together means a failed handler releases the claim and the retry
-- reprocesses cleanly.  See `claim_stripe_event` in src/db/subscriptions.py.
--
-- This table records events RECEIVED AND PROCESSED, not events accepted.  Rows
-- are only inserted after signature verification passes, so it can never be
-- grown by an unauthenticated caller.
--
-- Migrations are applied MANUALLY in sorted order; prod deploys do NOT run them
-- (see CLAUDE.md).  Apply with `psql -v ON_ERROR_STOP=1`.

CREATE TABLE IF NOT EXISTS processed_stripe_events (
    -- Stripe's own event id (`evt_...`).  Natural primary key: it is globally
    -- unique, stable across retries of the same event, and supplied by the
    -- sender, which is exactly what makes it usable as a dedupe key.
    event_id     TEXT        PRIMARY KEY,
    -- Retained for operator triage ("what did we actually process last night?").
    -- Not used in any decision — the primary key alone drives dedupe.
    event_type   TEXT        NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Supports pruning.  The table grows by one row per Stripe event forever, which
-- at this volume is trivial (a few rows per subscriber per month) but unbounded.
-- Stripe retries a failed delivery for up to ~3 days, so a row older than that
-- can never be needed for dedupe again.  Prune well past that window, e.g.:
--
--   DELETE FROM processed_stripe_events WHERE processed_at < NOW() - INTERVAL '90 days';
--
-- No automatic job is installed: at the expected volume this table will not need
-- pruning for years, and a silent DELETE job around payment state is worse than
-- an operator running one line when it matters.
CREATE INDEX IF NOT EXISTS idx_processed_stripe_events_processed_at
    ON processed_stripe_events (processed_at);
