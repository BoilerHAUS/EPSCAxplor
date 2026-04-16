-- Migration 004: Create api_keys table

CREATE TABLE api_keys (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash     TEXT        NOT NULL UNIQUE,                -- Store hash, never plaintext
    name         TEXT        NOT NULL,                       -- Human label, e.g. "Production API Key"
    last_used_at TIMESTAMPTZ,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No updated_at: api_keys rows are rotated (delete + insert), not mutated
);

CREATE INDEX idx_api_keys_tenant_id ON api_keys(tenant_id);
