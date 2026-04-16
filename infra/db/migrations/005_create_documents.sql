-- Migration 005: Create documents table
-- Source of truth for every ingested document; enables re-ingestion, version tracking,
-- and expiry flagging.

CREATE TABLE documents (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    union_name       TEXT        NOT NULL,                   -- e.g. 'IBEW', 'Sheet Metal'
    document_type    TEXT        NOT NULL
                     CHECK (document_type IN (
                         'primary_ca',
                         'nuclear_pa',
                         'moa_supplement',
                         'wage_schedule'
                     )),
    agreement_scope  TEXT,                                   -- 'generation', 'transmission', or NULL
    title            TEXT        NOT NULL,                   -- Full document title as on EPSCA site
    source_url       TEXT,                                   -- Original download URL (NULL for manually downloaded)
    source_filename  TEXT        NOT NULL,                   -- Original filename
    effective_date   DATE,                                   -- Agreement or wage schedule effective date
    expiry_date      DATE,                                   -- Agreement expiry date (NULL if ongoing)
    is_expired       BOOLEAN     NOT NULL DEFAULT FALSE,
    file_hash        TEXT        NOT NULL,                   -- SHA-256 of the PDF for change detection
    chunk_count      INTEGER,                                -- Populated after ingestion
    ingested_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_union_name     ON documents(union_name);
CREATE INDEX idx_documents_document_type  ON documents(document_type);

CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
