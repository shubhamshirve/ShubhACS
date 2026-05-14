# Agent Handoff Document

This document contains operational and architectural insights intended to streamline onboarding for future developer agents working on this codebase.

## High-Level Architecture
*   **Frontend**: React + Shadcn CSS serving on port `80`. All requests to `/api/*` are automatically proxied upstream through the Caddy Server container.
*   **Backend**: FastAPI (Uvicorn) serving on internal port `8001`. 
*   **Proxy**: Caddy orchestrates public URL management, automated SSL generation, and routing.
*   **Database**: MongoDB 7 running inside a dedicated overlay network, with persistent volumes defined as `acs_mongo_data`.

## Key Fixes Done (May 2026)
1.  **Concurrency Safeguards (`backend/server.py`)**: 
    The backend previously instantiated indexes AFTER seeding the Super Admin, crashing whenever multi-worker uvicorn containers spawned parallel lifecycle events. We rearranged it to construct Unique Indexes first and added explicit exception traps to handle race conditions safely.
2.  **Docker Build Optimization**:
    Removed hard dependency on missing `yarn.lock` from `frontend/Dockerfile` allowing the container runtime to build the package bundles statically.

## Technical Notes for Future Actions
*   **Multiple Workers Support**: The system is now natively configured for multiple workers. If you change scaling in `docker-compose` or backend `Dockerfile`, the startup process is fully idempotent and safe.
*   **Environment Management**: Ensure a valid `.env` exists at the root of the repository. Do not check sensitive `.env` keys into Git history.
*   **Server Ports**: Runs default on `80`/`443`. Watch out for port collision errors with other localized web applications (e.g. `ebill`).
