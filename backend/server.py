from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from database import init_db, get_db
from auth_utils import hash_password, verify_password
from pymongo.errors import DuplicateKeyError

from routes.auth import router as auth_router
from routes.operators import router as operators_router
from routes.users import router as users_router
from routes.devices import router as devices_router
from routes.diagnostics import router as diagnostics_router
from routes.settings import router as settings_router
from routes.router_models import router as router_models_router
from routes.stats import router as stats_router
from routes.acs import router as acs_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="ACS Management Server - India", version="1.0.0")

# Build CORS origins list — supports CORS_ORIGINS env var (comma-separated)
_raw_cors = os.environ.get("CORS_ORIGINS", "").strip()
if _raw_cors and _raw_cors != "*":
    _cors_origins = [o.strip() for o in _raw_cors.split(",") if o.strip()]
else:
    _cors_origins = list({
        os.environ.get("FRONTEND_URL", "http://localhost"),
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    })

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(operators_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(devices_router, prefix=API_PREFIX)
app.include_router(diagnostics_router, prefix=API_PREFIX)
app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(router_models_router, prefix=API_PREFIX)
app.include_router(stats_router, prefix=API_PREFIX)
app.include_router(acs_router, prefix=API_PREFIX)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ACS Management Server"}


@app.on_event("startup")
async def startup():
    await init_db()
    db = get_db()
    await create_indexes(db)
    await seed_data(db)
    logger.info("ACS Server started successfully")


async def seed_data(db):
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@acsserver.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        try:
            await db.users.insert_one({
                "_id": str(uuid.uuid4()),
                "email": admin_email,
                "password_hash": hash_password(admin_password),
                "name": "Super Admin",
                "role": "super_admin",
                "operator_id": None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"Super admin seeded: {admin_email}")
        except DuplicateKeyError:
            logger.info(f"Super admin already seeded by another worker: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}}
        )

    existing_settings = await db.settings.find_one({"_id": "global"})
    if not existing_settings:
        backend_url = os.environ.get("FRONTEND_URL", "https://analyze-app-8.preview.emergentagent.com")
        try:
            await db.settings.insert_one({
                "_id": "global",
                "ai_enabled": False,
                "gemini_api_key": "",
                "speed_test_enabled": True,
                "diagnostics_enabled": True,
                "tr069_enabled": True,
                "tr369_enabled": True,
                "acs_url": f"{backend_url}/api/acs/cwmp",
                "cwmp_username": "acs",
                "cwmp_password": "acs123",
                "inform_interval": 300,
            })
        except DuplicateKeyError:
            pass

    count = await db.router_models.count_documents({})
    if count == 0:
        sample_models = [
            {"brand": "Huawei", "model": "HG8245H", "isps": ["BSNL", "MTNL"], "protocols": ["TR-069"], "chipset": "HiSilicon Hi1151V100", "category": "GPON ONT", "ports": {"lan": 4, "usb": 1}, "is_active": True},
            {"brand": "Huawei", "model": "EG8145V5", "isps": ["BSNL", "MTNL", "Generic"], "protocols": ["TR-069", "TR-369"], "chipset": "HiSilicon SD5115T", "category": "GPON ONT", "ports": {"lan": 4, "usb": 1, "phone": 1}, "is_active": True},
            {"brand": "ZTE", "model": "F660", "isps": ["BSNL", "MTNL"], "protocols": ["TR-069"], "chipset": "ZTE ZX279127", "category": "GPON ONT", "ports": {"lan": 4}, "is_active": True},
            {"brand": "ZTE", "model": "F670L", "isps": ["BSNL", "ACT Fibernet"], "protocols": ["TR-069", "TR-369"], "chipset": "ZTE ZX279128S", "category": "GPON ONT", "ports": {"lan": 4, "usb": 1}, "is_active": True},
            {"brand": "Nokia", "model": "G-240G-A", "isps": ["Airtel"], "protocols": ["TR-069", "TR-369"], "chipset": "Broadcom BCM68360", "category": "GPON ONT", "ports": {"lan": 4, "usb": 1}, "is_active": True},
            {"brand": "Nokia", "model": "G-010S-P", "isps": ["Airtel", "ACT Fibernet"], "protocols": ["TR-069"], "chipset": "Broadcom BCM68620", "category": "SFP ONT", "ports": {"sfp": 1}, "is_active": True},
            {"brand": "Technicolor", "model": "TC8717T", "isps": ["Airtel"], "protocols": ["TR-069"], "chipset": "Broadcom BCM3385", "category": "VDSL2 Router", "ports": {"lan": 4, "usb": 1, "phone": 2}, "is_active": True},
            {"brand": "Sagemcom", "model": "F@ST 2864", "isps": ["Airtel", "ACT Fibernet"], "protocols": ["TR-069"], "chipset": "Broadcom BCM63168", "category": "ADSL2+ Router", "ports": {"lan": 4, "usb": 1, "adsl": 1}, "is_active": True},
            {"brand": "D-Link", "model": "DWR-932", "isps": ["Jio", "Generic"], "protocols": ["TR-069"], "chipset": "Qualcomm MDM9215", "category": "4G LTE Router", "ports": {"lan": 1, "usb": 1}, "is_active": True},
            {"brand": "TP-Link", "model": "TD-W9970", "isps": ["BSNL", "Generic"], "protocols": ["TR-069"], "chipset": "MediaTek MT7510", "category": "VDSL2 Router", "ports": {"lan": 4, "usb": 1}, "is_active": True},
            {"brand": "TP-Link", "model": "Archer VR900", "isps": ["Generic", "Airtel"], "protocols": ["TR-069", "TR-369"], "chipset": "MediaTek MT7621", "category": "VDSL2 AC Router", "ports": {"lan": 4, "usb": 2}, "is_active": True},
            {"brand": "Netgear", "model": "DGN2200", "isps": ["Generic"], "protocols": ["TR-069"], "chipset": "Broadcom BCM6362", "category": "ADSL2+ Router", "ports": {"lan": 4}, "is_active": True},
            {"brand": "UTStarcom", "model": "AN5506-04-F", "isps": ["BSNL"], "protocols": ["TR-069"], "chipset": "EcoNet EN7512", "category": "GPON ONT", "ports": {"lan": 4, "phone": 2}, "is_active": True},
            {"brand": "Arcadyan", "model": "VR9517", "isps": ["ACT Fibernet"], "protocols": ["TR-069", "TR-369"], "chipset": "MediaTek MT7621S", "category": "Fiber Router", "ports": {"lan": 4, "usb": 1}, "is_active": True},
            {"brand": "Syrotech", "model": "SY-GPON-1110-WDONT", "isps": ["BSNL", "MTNL", "Generic"], "protocols": ["TR-069"], "chipset": "Realtek RTL9607C", "category": "GPON ONT", "ports": {"lan": 4, "usb": 1}, "is_active": True},
            {"brand": "Tenda", "model": "HG9", "isps": ["Generic", "ACT Fibernet"], "protocols": ["TR-069"], "chipset": "MediaTek MT7620A", "category": "GPON ONT", "ports": {"lan": 4}, "is_active": True},
            {"brand": "ASUS", "model": "DSL-AC68U", "isps": ["Generic"], "protocols": ["TR-069", "TR-369"], "chipset": "Broadcom BCM63138", "category": "VDSL2 AC Router", "ports": {"lan": 4, "usb": 2}, "is_active": True},
            {"brand": "Mikrotik", "model": "RB951Ui-2nD", "isps": ["Generic"], "protocols": ["TR-069"], "chipset": "Atheros AR9331", "category": "Wireless Router", "ports": {"lan": 4, "usb": 1}, "is_active": True},
        ]
        now_iso = datetime.now(timezone.utc).isoformat()
        for m in sample_models:
            m["_id"] = str(uuid.uuid4())
            m["created_at"] = now_iso
            m["notes"] = ""
        try:
            await db.router_models.insert_many(sample_models)
            logger.info(f"Seeded {len(sample_models)} router models")
        except DuplicateKeyError:
            pass

    import os as _os
    _os.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write(f"""# ACS Server Test Credentials

## Super Admin
- Email: {admin_email}
- Password: {admin_password}
- Role: super_admin

## API Endpoints
- Login: POST /api/auth/login
- Me: GET /api/auth/me
- Logout: POST /api/auth/logout
- Devices: GET /api/devices
- Operators: GET /api/operators
- Settings: GET /api/settings
- Stats: GET /api/stats
- ACS CWMP: POST /api/acs/cwmp
- ACS USP: POST /api/acs/usp/register
""")


async def create_indexes(db):
    await db.users.create_index("email", unique=True)
    await db.devices.create_index("serial_number", unique=True, sparse=True)
    await db.devices.create_index("operator_id")
    await db.devices.create_index("status")
    await db.diagnostics.create_index("device_id")
    await db.diagnostics.create_index("created_at")
    await db.operators.create_index("code", unique=True)


@app.on_event("shutdown")
async def shutdown():
    from database import _client
    if _client:
        _client.close()
