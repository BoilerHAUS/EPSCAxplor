-- Migration 006: Create query_logs table
-- Every query is logged for auditing, debugging, and future analytics.

CREATE TABLE query_logs (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID        NOT NULL REFERENCES tenants(id),
    user_id           UUID        REFERENCES users(id),      -- NULL for API key queries
    query_text        TEXT        NOT NULL,
    response_text     TEXT        NOT NULL,
    model_used        TEXT        NOT NULL,                  -- 'claude-haiku-4-5-20251001' or 'claude-sonnet-4-6'
    union_filter      TEXT[],                                -- Unions filtered before retrieval, if any
    doc_type_filter   TEXT[],                                -- Document types filtered, if any
    chunks_retrieved  INTEGER     NOT NULL,
    prompt_tokens     INTEGER     NOT NULL,
    completion_tokens INTEGER     NOT NULL,
    latency_ms        INTEGER     NOT NULL,
    citations         JSONB,                                 -- Structured citation data extracted from response
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- No updated_at: query_logs are append-only, never mutated
);

CREATE INDEX idx_query_logs_tenant_id  ON query_logs(tenant_id);
CREATE INDEX idx_query_logs_user_id    ON query_logs(user_id);
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at);
