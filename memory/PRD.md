# ACS Server - SaaS Platform PRD

## Original Problem Statement
Create a SaaS ACS Server which supports all Indian routers and provides configuration and diagnostics details. Admin panel to manage operators and operator panels will manage their subscribers (staff). Addition and management of routers should be simple. WAN, WiFi, Speed Test and status details should be present and editable. UI needs to be responsive and easy to use.

## Architecture

### Stack
- **Frontend**: React + Tailwind CSS + Shadcn UI + @phosphor-icons/react
- **Backend**: FastAPI + MongoDB
- **AI**: Gemini 3 Flash (via emergentintegrations library)
- **Auth**: JWT with httpOnly cookies, bcrypt password hashing

### Backend Structure
```
/app/backend/
├── server.py           # Main FastAPI app, startup seed
├── database.py         # MongoDB singleton
├── auth_utils.py       # JWT, bcrypt, dependencies
└── routes/
    ├── auth.py         # Login, logout, me, refresh, change-password
    ├── operators.py    # Operator CRUD (super_admin only)
    ├── users.py        # User/Staff CRUD
    ├── devices.py      # Device CRUD + WAN/WiFi config
    ├── diagnostics.py  # Ping, traceroute, speedtest, AI analysis
    ├── settings.py     # Global settings (AI toggle, ACS config)
    ├── router_models.py # Router model library
    ├── stats.py        # Dashboard statistics
    └── acs.py          # TR-069 CWMP + TR-369 USP endpoints
```

### Frontend Structure
```
/app/frontend/src/
├── App.js              # React Router with protected routes
├── context/
│   └── AuthContext.js  # Auth state + login/logout
├── components/
│   ├── Layout.js       # Sidebar + main layout
│   └── ProtectedRoute.js # Role-based route guard
└── pages/
    ├── LoginPage.js    # Split login page
    ├── Dashboard.js    # Role-aware KPI dashboard
    ├── DeviceList.js   # Device table with filters
    ├── DeviceDetail.js # Device tabs (Overview/WAN/WiFi/Diagnostics/AI)
    ├── UserManagement.js # Operators + Users tabs
    ├── GlobalSettings.js # AI/ACS/Feature settings
    └── RouterModels.js # Router library grid
```

## User Roles
| Role | Access |
|------|--------|
| super_admin | Full platform access, manage operators, global settings |
| operator | Manage own devices and staff |
| staff | View/diagnostics on operator's devices |

## What's Been Implemented (April 2026)

### Core Features
- ✅ JWT authentication with role-based access (super_admin, operator, staff)
- ✅ Operator management (CRUD)
- ✅ User/Staff management (CRUD + password reset)
- ✅ Device management (CRUD) with TR-069/TR-369/Both protocol support
- ✅ WAN configuration (PPPoE, DHCP, Static with VLAN, MTU)
- ✅ WiFi configuration (2.4GHz + 5GHz, channel, security, bandwidth)
- ✅ Ping diagnostics (real subprocess)
- ✅ Traceroute diagnostics (real subprocess)
- ✅ Speed test (simulated realistic values)
- ✅ AI diagnostics (Gemini 3 Flash, requires API key or Universal Key)
- ✅ Real-time device status (online/offline/unknown)
- ✅ TR-069 CWMP ACS endpoint (/api/acs/cwmp) — auto-registers devices
- ✅ TR-369 USP ACS endpoint (/api/acs/usp/register)
- ✅ Router model library (18 Indian ISP models pre-seeded)
- ✅ Global settings with AI toggle, Gemini API key input
- ✅ Feature toggles (diagnostics, speed test, AI)
- ✅ ACS CWMP configuration panel with provisioning template

### Seeded Router Models
- Huawei HG8245H, EG8145V5 (BSNL/MTNL)
- ZTE F660, F670L (BSNL/MTNL/ACT)
- Nokia G-240G-A, G-010S-P (Airtel)
- Technicolor TC8717T (Airtel)
- Sagemcom F@ST 2864 (Airtel/ACT)
- D-Link DWR-932 (Jio)
- TP-Link TD-W9970, Archer VR900 (Generic/Airtel)
- Netgear DGN2200 (Generic)
- UTStarcom AN5506-04-F (BSNL)
- Arcadyan VR9517 (ACT)
- Syrotech SY-GPON-1110-WDONT (BSNL/MTNL)
- Tenda HG9, ASUS DSL-AC68U, Mikrotik RB951

## Prioritized Backlog

### P0 (Critical - Next Phase)
- [ ] Real-time device status via WebSocket or polling
- [ ] Firmware upgrade management
- [ ] Device grouping/tagging

### P1 (High Priority)
- [ ] Brute force login protection (rate limiting)
- [ ] Audit logs page
- [ ] Operator dashboard with their own stats
- [ ] Bulk device provisioning via CSV import
- [ ] Email notifications (device offline alerts)

### P2 (Nice to Have)
- [ ] Subscriber portal (read-only)
- [ ] Device configuration templates
- [ ] Historical speed test charts
- [ ] Multi-language support (Hindi etc.)

## API Endpoints Reference
- POST /api/auth/login
- GET /api/auth/me
- GET /api/stats
- GET/POST/PUT/DELETE /api/devices
- GET/PUT /api/devices/{id}/wan
- GET/PUT /api/devices/{id}/wifi
- POST /api/diagnostics/{id}/ping
- POST /api/diagnostics/{id}/traceroute
- POST /api/diagnostics/{id}/speedtest
- POST /api/diagnostics/{id}/ai-analyze
- GET /api/diagnostics/{id}/history
- GET/POST/PUT/DELETE /api/operators
- GET/POST/PUT/DELETE /api/users
- GET/PUT /api/settings
- GET /api/settings/public
- GET/POST/PUT/DELETE /api/router-models
- POST /api/acs/cwmp (TR-069)
- POST /api/acs/usp/register (TR-369)
- GET /api/acs/status
