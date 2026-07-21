-- Migration 009: Normalize user email to lowercase + enforce case-insensitive uniqueness (#141)
--
-- Migration 002 declared `email TEXT NOT NULL UNIQUE`, which is case-sensitive: a
-- user created as You@x.com could not log in as you@x.com, and both could exist as
-- separate accounts. This migration folds email case so those are one account.
--
-- DDL/DML in PostgreSQL runs inside an implicit transaction, so the RAISE below
-- aborts and rolls back the ENTIRE file: a genuine collision leaves `users`
-- completely untouched. Apply with `psql -v ON_ERROR_STOP=1` so the operator
-- sees the non-zero exit. Migrations are applied manually in sorted order; prod
-- deploys do NOT run them (see CLAUDE.md).
--
-- OPERATIONAL NOTE: apply during a low-traffic window (ideally a brief pause on
-- login / user-creation). The GUARD and REPAIR take no table lock; the first
-- ACCESS EXCLUSIVE lock is acquired at the ALTER/CREATE INDEX step. A concurrent
-- write in that gap would at worst make CREATE UNIQUE INDEX fail and roll the
-- whole file back (safe — no data change), but a freeze avoids the wasted run.
-- Sanity-check the size first (expected: a handful of rows): SELECT count(*) FROM users;

-- 1. GUARD: refuse to proceed if two rows differ only by case. We never
--    auto-delete an account — the operator dedupes manually, then re-runs.
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT count(*) INTO dup_count FROM (
        SELECT lower(email) FROM users GROUP BY lower(email) HAVING count(*) > 1
    ) AS collisions;
    IF dup_count > 0 THEN
        RAISE EXCEPTION
            'Migration 009 aborted: % email(s) collide case-insensitively. '
            'Dedupe the duplicate users manually, then re-run.', dup_count;
    END IF;
END $$;

-- 2. REPAIR: lowercase any surviving mixed-case rows in place.
UPDATE users SET email = lower(email) WHERE email <> lower(email);

-- 3. ENFORCE: replace the case-sensitive UNIQUE constraint and its now-redundant
--    plain index with a single functional unique index on LOWER(email). This is
--    both the uniqueness guard and the index behind get_user_by_email's
--    `WHERE LOWER(email) = $1` lookup. IF EXISTS keeps it safe on any DB where
--    002's objects are already absent.
--    Dropping the old constraint before the replacement index exists is safe:
--    this file is one transaction and DROP CONSTRAINT takes ACCESS EXCLUSIVE, so
--    no other session can insert a colliding row in the gap — writers block until
--    this transaction commits (new index in place) or rolls back (old one intact).
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;
DROP INDEX IF EXISTS idx_users_email;
CREATE UNIQUE INDEX idx_users_email_lower ON users (lower(email));
