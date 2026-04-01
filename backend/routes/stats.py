from fastapi import APIRouter, Depends
from database import get_db
from auth_utils import get_current_user
from bson import ObjectId
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    query = {}
    if current_user["role"] in ["operator", "staff"]:
        query = {"operator_id": current_user["operator_id"]}

    total_devices = await db.devices.count_documents(query)
    online_devices = await db.devices.count_documents({**query, "status": "online"})
    offline_devices = await db.devices.count_documents({**query, "status": "offline"})
    unknown_devices = await db.devices.count_documents({**query, "status": "unknown"})

    tr069_devices = await db.devices.count_documents({**query, "protocol": "tr069"})
    tr369_devices = await db.devices.count_documents({**query, "protocol": "tr369"})
    both_devices = await db.devices.count_documents({**query, "protocol": "both"})

    stats = {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "unknown_devices": unknown_devices,
        "protocol_distribution": {
            "tr069": tr069_devices,
            "tr369": tr369_devices,
            "both": both_devices,
        },
    }

    if current_user["role"] == "super_admin":
        total_operators = await db.operators.count_documents({})
        active_operators = await db.operators.count_documents({"is_active": True})
        total_users = await db.users.count_documents({})
        stats.update({
            "total_operators": total_operators,
            "active_operators": active_operators,
            "total_users": total_users,
        })

    # Recent devices
    recent_devices = await db.devices.find(query).sort("created_at", -1).to_list(5)
    stats["recent_devices"] = [
        {
            "id": str(d["_id"]),
            "name": d.get("name", ""),
            "status": d.get("status", "unknown"),
            "manufacturer": d.get("manufacturer", ""),
            "model": d.get("model", ""),
            "ip_address": d.get("ip_address", ""),
            "created_at": d.get("created_at", ""),
        }
        for d in recent_devices
    ]

    # Diagnostics count last 7 days
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_diag = await db.diagnostics.count_documents({
        "created_at": {"$gte": week_ago},
        **({"device_id": {"$in": [str(d["_id"]) for d in await db.devices.find(query, {"_id": 1}).to_list(1000)]}} if query else {})
    })
    stats["diagnostics_this_week"] = recent_diag

    if current_user["role"] == "operator":
        staff_count = await db.users.count_documents({"operator_id": current_user["operator_id"], "role": "staff"})
        stats["staff_count"] = staff_count

    return stats
