-- Migration 001: Create tenants table and shared updated_at trigger
-- The trigger function is defined here and reused by all subsequent migrations.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE tenants (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name               TEXT        NOT NULL,
    slug               TEXT        NOT NULL UNIQUE,          -- URL-safe identifier, used for white-label routing
    tier               TEXT        NOT NULL
                       CHECK (tier IN ('individual', 'professional', 'enterprise')),
    is_white_label     BOOLEAN     NOT NULL DEFAULT FALSE,
    white_label_domain TEXT,                                 -- Custom domain for white-label deployments
    corpus_filter      JSONB,                                -- Optional: restrict accessible unions for this tenant
                                                             -- e.g. {"unions": ["IBEW", "Sheet Metal"]}
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
