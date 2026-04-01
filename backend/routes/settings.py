from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from database import get_db
from auth_utils import require_roles, get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


class GlobalSettings(BaseModel):
    ai_enabled: bool = False
    gemini_api_key: str = ""
    speed_test_enabled: bool = True
    diagnostics_enabled: bool = True
    tr069_enabled: bool = True
    tr369_enabled: bool = True
    acs_url: str = ""
    cwmp_username: str = "acs"
    cwmp_password: str = "acs123"
    inform_interval: int = 300


@router.get("")
async def get_settings(current_user: dict = Depends(require_roles("super_admin"))):
    db = get_db()
    settings = await db.settings.find_one({"_id": "global"})
    if not settings:
        return GlobalSettings().model_dump()
    settings.pop("_id", None)
    # Mask API key in response
    if settings.get("gemini_api_key"):
        key = settings["gemini_api_key"]
        settings["gemini_api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "****"
    else:
        settings["gemini_api_key_masked"] = ""
    return settings


@router.put("")
async def update_settings(
    data: GlobalSettings,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    update_dict = data.model_dump()
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_dict["updated_by"] = current_user["id"]
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": update_dict},
        upsert=True
    )
    settings = await db.settings.find_one({"_id": "global"})
    settings.pop("_id", None)
    if settings.get("gemini_api_key"):
        key = settings["gemini_api_key"]
        settings["gemini_api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "****"
    else:
        settings["gemini_api_key_masked"] = ""
    return settings


@router.get("/public")
async def get_public_settings(current_user: dict = Depends(get_current_user)):
    """Returns non-sensitive settings visible to all logged-in users"""
    db = get_db()
    settings = await db.settings.find_one({"_id": "global"})
    if not settings:
        return {"ai_enabled": False, "speed_test_enabled": True, "diagnostics_enabled": True}
    return {
        "ai_enabled": settings.get("ai_enabled", False),
        "speed_test_enabled": settings.get("speed_test_enabled", True),
        "diagnostics_enabled": settings.get("diagnostics_enabled", True),
        "tr069_enabled": settings.get("tr069_enabled", True),
        "tr369_enabled": settings.get("tr369_enabled", True),
        "acs_url": settings.get("acs_url", ""),
        "cwmp_username": settings.get("cwmp_username", "acs"),
        "inform_interval": settings.get("inform_interval", 300),
    }
