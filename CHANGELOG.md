# Changelog

All notable changes to EPSCAxplor are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- JWT authentication with refresh-token rotation (#23): `POST /auth/login`, `/auth/refresh`, and `/auth/logout`. Access tokens are short-lived HS256 JWTs; refresh tokens are opaque, stored only as SHA-256 hashes, and rotated per use within a login "family".
- Server-side refresh-token reuse detection — replaying a rotated token revokes the entire family.
- `refresh_tokens` table (migration 007) and a seeded bootstrap `system` tenant (migration 008, which also fixes the previously unseeded `query_logs` tenant FK).
- `scripts/create_user.py` operator CLI for creating tenant users with bcrypt-hashed passwords (no registration endpoint in Phase 3).
- Initial repository structure and GitHub workflow configuration

### Changed
- `/query` now requires a valid access JWT; `get_current_user` decodes the bearer token into tenant/user context, replacing the interim shared bearer token.
- CORS now sends `allow_credentials` so the httpOnly refresh cookie can round-trip (requires exact, non-wildcard `CORS_ORIGINS`).
- `/query` now returns a real `query_log_id` (previously `N/A`); query-log persistence moved into `src/db/query_logs.py` with unit coverage, and remains best-effort so a logging failure never fails the answer (#88).

### Removed
- Interim `QUERY_API_TOKEN` shared-secret protection on `/query`, superseded by JWT auth (#85 → #23).

### Security
- Passwords hashed with bcrypt (via the maintained `bcrypt` library, replacing the unmaintained `passlib`); JWT algorithm pinned to HS256 to block `alg=none`/confusion; uniform `401 unauthorized` on all auth failures to avoid user enumeration.
