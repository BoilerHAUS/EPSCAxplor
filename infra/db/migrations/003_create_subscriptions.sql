-- Migration 003: Create subscriptions table

CREATE TABLE subscriptions (
    id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tier                   TEXT        NOT NULL
                           CHECK (tier IN ('individual', 'professional', 'enterprise')),
    status                 TEXT        NOT NULL DEFAULT 'active'
                           CHECK (status IN ('active', 'cancelled', 'past_due', 'trialing')),
    stripe_customer_id     TEXT,
    stripe_subscription_id TEXT,
    query_limit_monthly    INTEGER,                          -- NULL means unlimited (enterprise)
    user_limit             INTEGER,                          -- NULL means unlimited (enterprise)
    current_period_start   TIMESTAMPTZ,
    current_period_end     TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
