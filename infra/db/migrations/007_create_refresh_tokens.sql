-- Migration 007: Create refresh_tokens table
-- Backs JWT refresh-token rotation (#23). Refresh tokens are opaque, high-entropy
-- strings; only their SHA-256 hash is stored (never plaintext, mirroring
-- api_keys.key_hash). Rotation lineage is tracked via family_id so that replaying
-- an already-rotated token can revoke the entire family (theft self-limits).

CREATE TABLE refresh_tokens (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    tenant_id  UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,  -- denormalized: rebuild the tenant claim without a users join
    token_hash TEXT        NOT NULL UNIQUE,                 -- SHA-256 hex of the raw token; never store plaintext
    family_id  UUID        NOT NULL,                        -- rotation lineage; all descendants of one login share it
    parent_id  UUID        REFERENCES refresh_tokens(id) ON DELETE SET NULL,   -- token this one replaced (audit of the chain)
    status     TEXT        NOT NULL DEFAULT 'active'
               CHECK (status IN ('active', 'rotated', 'revoked')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ
    -- No updated_at/trigger: rows transition status explicitly (active -> rotated/revoked), not via the shared trigger
);

CREATE INDEX idx_refresh_tokens_user_id    ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family_id  ON refresh_tokens(family_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
