# Changelog

All notable changes to this project will be documented in this file.

## [1.3] - 2026-05-15

### Security Fixes
- **ACS credential encryption**: Operator `acs_password` values are now encrypted at rest using Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256). Key is derived from `JWT_SECRET` automatically — no extra env var needed. Existing plaintext passwords are handled transparently via graceful fallback in `decrypt_value()`.
- **CWMP auth hardening**: `acs.py` authentication changed from a single MongoDB query with plaintext password to query-by-username + application-layer decryption + comparison. Prevents sensitive data from traveling in MongoDB query filters.
- **Cookie `secure` flag**: `auth_utils.py` now reads `SECURE_COOKIES` from environment. Set to `true` when deploying behind HTTPS. `docker-compose.yml` and `.env` updated with this flag.
- **Login rate limiting**: Added sliding-window brute-force protection (10 attempts / 60 seconds per IP) to the `/api/auth/login` endpoint via the new `rate_limiter.py` module. Counter clears on successful authentication.

### New Files
- `backend/crypto_utils.py` — Fernet encryption/decryption utilities with mask helper.
- `backend/rate_limiter.py` — In-memory thread-safe sliding-window rate limiter.

### New Endpoint
- `GET /api/operators/{op_id}/acs-credentials` — Super admin only. Returns decrypted ACS username and password for router CWMP configuration.

### API Behaviour Change
- `POST /api/operators` — Response now includes `acs_password_plain` (shown **once** at creation time only). Subsequent reads return a masked value (`xxxx****`).
- `GET /api/operators` / `GET /api/operators/{id}` — `acs_password` field is now masked in all responses.

---

## [1.2] - 2026-05-15

### Added
- Implemented robust MongoDB collection index creation on backend startup BEFORE seeding data, securing it against concurrency issues.
- Added graceful `pymongo.errors.DuplicateKeyError` exception handling during system seeding (`Super Admin`, `Global Settings`, `Router Models`) to facilitate robust deployment in multi-worker systems.
- Created comprehensive project documentation under `memory/` folder to satisfy enterprise handover guidelines (PRD enhancements, CHANGELOG, Agent Handoff).

### Fixed
- Fixed a major startup race condition in FastAPI backend when run with `workers > 1`, which led to a `DuplicateKeyError` on `email_1` during unique index application.
- Fixed frontend Docker image build failure due to a missing `yarn.lock` reference by restructuring `frontend/Dockerfile` to leverage dynamic lockfile synthesis.

### Deployment
- Fully automated stack composition and verification locally.
- Cleared conflicting port allocations with other legacy services (e.g., `ebill`) to facilitate successful local/production orchestration.

---

## [1.1] - 2026-04-30

### Added
- Baseline implementation of ACS TR-069 / TR-369 management endpoints.
- Full suite of Indian ISP router models seeded out of the box.
- Initial containerization via Docker and Compose.
