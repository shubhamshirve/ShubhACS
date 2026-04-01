# ACS Server — Docker Deployment Guide

## Quick Start (3 steps)

```bash
# 1. Clone and enter project
git clone <your-repo> && cd acs-server

# 2. Configure environment
cp .env.example .env
nano .env          # Set ACS_PUBLIC_URL and JWT_SECRET at minimum

# 3. Build and start
docker compose up -d --build
```

Open `http://your-server-ip` — login with the admin credentials from `.env`.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ACS_PUBLIC_URL` | **Yes** | `http://localhost` | Public URL of your ACS server (used in provisioning URLs) |
| `JWT_SECRET` | **Yes** | weak default | Random string for JWT signing — **change in production** |
| `ADMIN_EMAIL` | No | `admin@acsserver.com` | Super admin email (first-run only) |
| `ADMIN_PASSWORD` | No | `Admin@123` | Super admin password (first-run only) |
| `DB_NAME` | No | `acs_server_db` | MongoDB database name |
| `EMERGENT_LLM_KEY` | No | *(built-in)* | Gemini API key for AI diagnostics |
| `HTTP_PORT` | No | `80` | Host port for the web UI |
| `BACKEND_PORT` | No | `8001` | Host port for the API (internal use) |

---

## Architecture in Docker

```
Browser → :80 (nginx)
            ├── /api/*  → proxy → backend:8001 (FastAPI)
            │                          └── mongo:27017 (MongoDB)
            └── /*      → serve React SPA
```

---

## Useful Commands

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after code changes
docker compose up -d --build

# Stop
docker compose down

# Stop + remove data volume (WIPES DATABASE)
docker compose down -v

# Open a shell in backend container
docker compose exec backend bash

# Run MongoDB shell
docker compose exec mongo mongosh acs_server_db
```

---

## TR-069 Router Configuration

Once running, configure CPE devices to connect to your ACS:

| Field | Value |
|---|---|
| **ACS URL** | `http://your-server/api/acs/cwmp` |
| **ACS Username** | `acs` *(configurable in Global Settings)* |
| **ACS Password** | `acs123` *(configurable in Global Settings)* |
| **Periodic Inform** | Enable |
| **Inform Interval** | 300 seconds |

---

## HTTPS / TLS

For production, put a reverse proxy (nginx/Caddy/Traefik) in front:

**Caddy example (`/etc/caddy/Caddyfile`):**
```
acs.yourdomain.com {
    reverse_proxy localhost:80
}
```

Then update `.env`:
```
ACS_PUBLIC_URL=https://acs.yourdomain.com
```

Rebuild frontend: `docker compose up -d --build frontend`

---

## Upgrading

```bash
git pull
docker compose up -d --build
```

Data persists in the `acs_mongo_data` Docker volume.
