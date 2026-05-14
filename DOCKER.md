# ACS Server — Deployment Guide

> **Why you can't use the preview URL for CWMP:**
> The Emergent preview is a temporary sandbox. Your router needs to reach the ACS
> server 24/7 from the internet. You need a **public VPS** or **port-forwarded home server**.

---

## Architecture

```
Internet
   │
   ▼
Caddy :80/:443          ← auto SSL (Let's Encrypt), reverse proxy
   ├── /api/*  ──────►  FastAPI backend :8001
   └── /*      ──────►  React + nginx :80
                              │
                         MongoDB :27017
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Ubuntu 22.04 VPS | 1 vCPU / 1 GB RAM minimum. DigitalOcean ($6/mo), Hetzner (€4/mo), AWS Lightsail, etc. |
| Public IP | Assigned by your VPS provider |
| Domain name | Optional but required for HTTPS. Point an A-record to your VPS IP |
| Ports 80 + 443 open | See firewall section below |

---

## Step 1 — Open Firewall Ports

### On the VPS (Ubuntu ufw)
```bash
sudo ufw allow 22       # SSH — already open, don't skip this!
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 443/udp  # HTTP/3 (optional)
sudo ufw enable
sudo ufw status         # verify
```

### On your VPS provider's dashboard
Also open ports in the **cloud firewall / security group** — this is separate from ufw:

| Provider | Where to find it |
|----------|------------------|
| DigitalOcean | Networking → Firewalls |
| AWS EC2 | Security Groups → Inbound Rules |
| Hetzner | Firewall → Add Rule |
| Vultr | Settings → Firewall |

Add inbound rules: **TCP 80** and **TCP 443** from `0.0.0.0/0`.

---

## Step 2 — Install Docker

```bash
# Install Docker (official script)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

---

## Step 3 — Deploy the App

```bash
# 1. Upload / clone your project
git clone <your-repo-url> acs-server
cd acs-server

# 2. Create your config
cp .env.example .env
nano .env          # edit the values (see below)
```

### Minimum `.env` settings

**Option A — With a domain (recommended, auto-HTTPS):**
```env
ACS_PUBLIC_URL=https://acs.yourdomain.com
ACS_DOMAIN=acs.yourdomain.com
JWT_SECRET=<output of: openssl rand -hex 32>
ADMIN_PASSWORD=YourStrongPassword
```

**Option B — IP only (plain HTTP):**
```env
ACS_PUBLIC_URL=http://203.0.113.10
ACS_DOMAIN=
JWT_SECRET=<output of: openssl rand -hex 32>
ADMIN_PASSWORD=YourStrongPassword
```

```bash
# 3. Build and start (first run takes ~3 minutes)
docker compose up -d --build

# 4. Watch startup logs
docker compose logs -f
# Wait until you see: "Application startup complete"

# 5. Open in browser
#    https://acs.yourdomain.com  (with domain)
#    http://203.0.113.10         (IP only)
```

Default login: `admin@acsserver.com` / `Admin@123` (change in `.env` before deploy).

---

## Step 4 — Configure Your Router (CWMP / TR-069)

### Where to get the credentials
1. Log into the ACS web app
2. Go to **User Management → Operators**
3. Click **+ Add Operator** (or edit existing)
4. Copy the values from the **Router ACS Credentials** section

### TP-Link CWMP Settings

| Field | Value |
|-------|-------|
| CWMP | ✅ Enable |
| Inform | ✅ Enable |
| Inform Interval | `300` (seconds, not 10) |
| ACS URL | `https://acs.yourdomain.com/api/acs/cwmp` |
| ACS Username | *(operator's acs_username from the app)* |
| ACS Password | *(operator's acs_password from the app)* |
| Connection Request Auth | Optional |

The router will connect within `Inform Interval` seconds. You'll see it appear in **Devices** with status **Online** and auto-assigned to the correct operator.

---

## Home Network Deployment (behind a home router)

If running on a home server (Raspberry Pi, NUC, etc.):

1. **Port forward** on your home router:
   - External port `80` → Server LAN IP, port `80`
   - External port `443` → Server LAN IP, port `443`

2. **Get your public IP**: `curl ifconfig.me`

3. Use a **DDNS service** (No-IP, DuckDNS) to get a stable hostname since home IPs change.

> ⚠️ **Important**: If the TP-Link router IS your home router, it may not be able to reach an ACS server behind itself (NAT loopback issue). Use the **LAN IP** of the server as the ACS URL in that case, e.g. `http://192.168.1.100/api/acs/cwmp`.

---

## Management Commands

```bash
# View live logs
docker compose logs -f

# Restart all services
docker compose restart

# Stop everything
docker compose down

# Update to latest code (pull → rebuild)
git pull
docker compose up -d --build

# View running containers
docker compose ps

# Backup MongoDB data
docker exec acs_mongo mongodump --out /backup
docker cp acs_mongo:/backup ./mongo-backup-$(date +%Y%m%d)
```

---

## SSL Certificate (Caddy auto-handles this)

When `ACS_DOMAIN` is set to a real domain, Caddy automatically:
- Obtains a free SSL certificate from Let's Encrypt on first startup
- Renews it before expiry
- Redirects HTTP → HTTPS

**Requirements for auto-SSL:**
- Domain must have an A-record pointing to your server IP
- Port 80 must be open (Let's Encrypt HTTP challenge uses it)
- The domain must be reachable from the internet

---

## Troubleshooting

```bash
# Caddy logs (SSL issues, routing)
docker compose logs caddy

# Backend logs (API errors)
docker compose logs backend

# Frontend logs
docker compose logs frontend

# Test if backend is reachable from Caddy
docker exec acs_caddy wget -qO- http://backend:8001/api/health

# Test CWMP endpoint
curl -X POST https://yourdomain.com/api/acs/cwmp \
  -H "Authorization: Basic $(echo -n 'acs_user:acs_pass' | base64)" \
  -H "Content-Type: text/xml" \
  --data "" -v
```

### Common issues

| Symptom | Fix |
|---------|-----|
| Caddy shows certificate error | Check domain A-record points to server IP. Allow port 80 (needed for Let's Encrypt challenge) |
| Devices not appearing after router Inform | Check CWMP URL is correct. Check credentials match operator's ACS username/password |
| 401 on CWMP | Wrong ACS username/password. Check Operators page for correct values |
| Can't open app in browser | Check `ufw status` and cloud firewall rules — ports 80 and 443 must be open |
| Backend unhealthy | `docker compose logs backend` — usually a DB connection issue on first start |
