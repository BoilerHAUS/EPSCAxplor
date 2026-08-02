-- Migration 010: Allow the `general` document_type (#179)
--
-- Migration 005 created `documents.document_type` with an inline CHECK covering
-- the four agreement/rate types (primary_ca, nuclear_pa, moa_supplement,
-- wage_schedule).  EPSCA also publishes per-union ADMINISTRATIVE documents that
-- are none of those — the first is the Teamsters "Union Dues" form, which
-- states each local's dues formula and remittance address.  It is not an
-- agreement, not an MOA, and not a rate table (routing it to `wage_schedule`
-- would send it through the EPSCA wage-form parser, which expects classification
-- rate rows it does not have).  `general` is that lane.  It is still union-scoped
-- like every other type: `general` says "administrative, not an agreement", it
-- does NOT mean corpus-wide.
--
-- An inline CHECK gets the auto-generated name `documents_document_type_check`,
-- so this migration drops that constraint and re-adds it by the same name with
-- the extra value — leaving the schema identical to what a fresh 005+010 apply
-- produces.  DDL in PostgreSQL runs inside an implicit transaction and both
-- statements take ACCESS EXCLUSIVE on `documents`, so no session can insert an
-- unchecked row in the gap between the DROP and the ADD: writers block until
-- this file commits (new constraint in place) or rolls back (old one intact).
--
-- ADD CONSTRAINT ... CHECK validates every existing row before it commits.  That
-- is a full scan under an exclusive lock, but `documents` holds one row per
-- ingested PDF (low hundreds), so it is effectively instant and needs no
-- NOT VALID / VALIDATE CONSTRAINT split.  Migrations are applied manually in
-- sorted order; prod deploys do NOT run them (see CLAUDE.md).  Apply with
-- `psql -v ON_ERROR_STOP=1` so a failure is visible to the operator.
--
-- IF EXISTS keeps the DROP safe on a database where the constraint was already
-- renamed or removed; the widened CHECK is a strict superset of the old one, so
-- re-applying this file is harmless.  The name below is PostgreSQL's own
-- auto-generated one for 005's inline CHECK ({table}_{column}_check).  If it is
-- ever renamed out-of-band the DROP silently no-ops, but the ADD then fails
-- loudly on the duplicate name rather than leaving two constraints — check with
-- `\d documents` or `SELECT conname FROM pg_constraint WHERE conrelid =
-- 'documents'::regclass`.
--
-- WHEN COPYING THIS FILE for the next document_type change: the "harmless to
-- re-apply" and "no NOT VALID needed" reasoning holds only because this change
-- ADDS a value.  REMOVING one needs a pre-check for rows still using it (the
-- shape of 009's collision GUARD), or ADD CONSTRAINT fails validating them.

ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_document_type_check;

ALTER TABLE documents ADD CONSTRAINT documents_document_type_check
    CHECK (document_type IN (
        'primary_ca',
        'nuclear_pa',
        'moa_supplement',
        'wage_schedule',
        'general'
    ));
