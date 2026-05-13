from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from database import get_db
from auth_utils import get_current_user
from utils import find_by_id, new_id

router = APIRouter(prefix="/devices", tags=["devices"])


def serialize(doc: dict) -> dict:
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


class WanConfig(BaseModel):
    mode: str = "dhcp"
    connection_type: str = "ethernet"
    ip_address: str = ""
    subnet_mask: str = ""
    gateway: str = ""
    dns_primary: str = "8.8.8.8"
    dns_secondary: str = "8.8.4.4"
    pppoe_username: str = ""
    pppoe_password: str = ""
    service_name: str = ""
    vlan_id: Optional[int] = None
    mtu: int = 1500


class WifiConfig(BaseModel):
    band: str = "2.4GHz"
    ssid: str = ""
    password: str = ""
    security: str = "WPA2"
    channel: str = "auto"
    bandwidth: str = "20MHz"
    enabled: bool = True
    hidden: bool = False
    tx_power: str = "auto"
    max_clients: int = 32


class DeviceCreate(BaseModel):
    name: str
    serial_number: str
    mac_address: str = ""
    ip_address: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    protocol: str = "tr069"
    operator_id: str
    location: str = ""
    notes: str = ""


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    protocol: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


def get_scoped_query(current_user: dict, operator_id: Optional[str] = None) -> dict:
    query = {}
    if current_user["role"] in ["operator", "staff"]:
        query["operator_id"] = current_user["operator_id"]
    elif operator_id:
        query["operator_id"] = operator_id
    return query


@router.get("")
async def list_devices(
    status: Optional[str] = None,
    protocol: Optional[str] = None,
    operator_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    query = get_scoped_query(current_user, operator_id)
    if status:
        query["status"] = status
    if protocol:
        query["protocol"] = protocol
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"serial_number": {"$regex": search, "$options": "i"}},
            {"ip_address": {"$regex": search, "$options": "i"}},
            {"mac_address": {"$regex": search, "$options": "i"}},
            {"model": {"$regex": search, "$options": "i"}},
        ]
    devices = await db.devices.find(query).sort("created_at", -1).to_list(1000)
    result = []
    for d in devices:
        d = serialize(d)
        op = await find_by_id(db.operators, d["operator_id"]) if d.get("operator_id") else None
        d["operator_name"] = op["name"] if op else "Unknown"
        result.append(d)
    return result


@router.get("/status-updates")
async def get_device_status_updates(current_user: dict = Depends(get_current_user)):
    """Lightweight endpoint for real-time device status polling."""
    db = get_db()
    query = get_scoped_query(current_user)
    devices = await db.devices.find(
        query,
        {"_id": 1, "status": 1, "last_seen": 1, "ip_address": 1}
    ).to_list(1000)
    return [
        {
            "id": str(d["_id"]),
            "status": d.get("status", "unknown"),
            "last_seen": d.get("last_seen"),
            "ip_address": d.get("ip_address", ""),
        }
        for d in devices
    ]


@router.get("/{device_id}")
async def get_device(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"]:
        if device.get("operator_id") != current_user["operator_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
    d = serialize(device)
    op = await find_by_id(db.operators, d["operator_id"]) if d.get("operator_id") else None
    d["operator_name"] = op["name"] if op else "Unknown"
    return d


@router.post("")
async def create_device(data: DeviceCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot add devices")
    if current_user["role"] == "operator" and data.operator_id != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Cannot add device to another operator")

    existing = await db.devices.find_one({"serial_number": data.serial_number})
    if existing:
        raise HTTPException(status_code=400, detail="Serial number already registered")

    provision_code = str(uuid.uuid4())[:8].upper()
    doc = {
        "_id": new_id(),
        **data.model_dump(),
        "status": "unknown",
        "provision_code": provision_code,
        "wan_config": WanConfig().model_dump(),
        "wifi_config_2g": WifiConfig(band="2.4GHz").model_dump(),
        "wifi_config_5g": WifiConfig(band="5GHz", channel="36", bandwidth="80MHz").model_dump(),
        "last_seen": None,
        "uptime": 0,
        "connected_clients": 0,
        "signal_strength": None,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.devices.insert_one(doc)
    return serialize(doc)


@router.put("/{device_id}")
async def update_device(
    device_id: str,
    data: DeviceUpdate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot edit devices")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.devices.update_one({"_id": device["_id"]}, {"$set": update_data})
    device = await find_by_id(db.devices, device_id)
    return serialize(device)


@router.delete("/{device_id}")
async def delete_device(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot delete devices")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.diagnostics.delete_many({"device_id": device_id})
    await db.devices.delete_one({"_id": device["_id"]})
    return {"message": "Device deleted"}


@router.get("/{device_id}/wan")
async def get_wan_config(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return device.get("wan_config", WanConfig().model_dump())


@router.put("/{device_id}/wan")
async def update_wan_config(
    device_id: str,
    config: WanConfig,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot modify WAN config")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.devices.update_one(
        {"_id": device["_id"]},
        {"$set": {"wan_config": config.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return config.model_dump()


@router.get("/{device_id}/wifi")
async def get_wifi_config(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "wifi_2g": device.get("wifi_config_2g", WifiConfig(band="2.4GHz").model_dump()),
        "wifi_5g": device.get("wifi_config_5g", WifiConfig(band="5GHz").model_dump()),
    }


@router.put("/{device_id}/wifi")
async def update_wifi_config(
    device_id: str,
    band: str,
    config: WifiConfig,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot modify WiFi config")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    field = "wifi_config_2g" if band == "2.4GHz" else "wifi_config_5g"
    await db.devices.update_one(
        {"_id": device["_id"]},
        {"$set": {field: config.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return config.model_dump()
