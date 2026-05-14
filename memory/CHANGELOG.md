# Changelog

All notable changes to this project will be documented in this file.

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
