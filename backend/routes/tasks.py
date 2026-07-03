"""
CWMP Task Queue — TR-069 RPC task management.
Tasks are dispatched to CPE devices on their next Inform cycle.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, Dict, List

from database import get_db
from auth_utils import get_current_user
from utils import find_by_id, new_id

router = APIRouter(prefix="/devices", tags=["tasks"])

TASK_TYPES = [
    "set_parameter_values",
    "reboot",
    "factory_reset",
    "get_parameter_values",
]

# ──────────────────────────────────────────────
# TR-181 (Device:2) parameter mapping
# ──────────────────────────────────────────────
WIFI_2G_PARAM_MAP = {
    "ssid":      "Device.WiFi.SSID.1.SSID",
    "enabled":   "Device.WiFi.SSID.1.Enable",
    "password":  "Device.WiFi.AccessPoint.1.Security.KeyPassphrase",
    "security":  "Device.WiFi.AccessPoint.1.Security.ModeEnabled",
    "channel":   "Device.WiFi.Radio.1.Channel",
    "bandwidth": "Device.WiFi.Radio.1.OperatingChannelBandwidth",
    "tx_power":  "Device.WiFi.Radio.1.TransmitPower",
}
WIFI_5G_PARAM_MAP = {
    "ssid":      "Device.WiFi.SSID.2.SSID",
    "enabled":   "Device.WiFi.SSID.2.Enable",
    "password":  "Device.WiFi.AccessPoint.2.Security.KeyPassphrase",
    "security":  "Device.WiFi.AccessPoint.2.Security.ModeEnabled",
    "channel":   "Device.WiFi.Radio.2.Channel",
    "bandwidth": "Device.WiFi.Radio.2.OperatingChannelBandwidth",
    "tx_power":  "Device.WiFi.Radio.2.TransmitPower",
}
WAN_PPPoE_PARAM_MAP = {
    "pppoe_username": "Device.PPP.Interface.1.Username",
    "pppoe_password": "Device.PPP.Interface.1.Password",
    "service_name":   "Device.PPP.Interface.1.Name",
    "mtu":            "Device.PPP.Interface.1.MaxMRUSize",
}
WAN_STATIC_PARAM_MAP = {
    "ip_address":  "Device.IP.Interface.1.IPv4Address.1.IPAddress",
    "subnet_mask": "Device.IP.Interface.1.IPv4Address.1.SubnetMask",
    "gateway":     "Device.Routing.Router.1.IPv4Forwarding.1.GatewayIPAddress",
}
WAN_COMMON_PARAM_MAP = {
    "dns_primary":   "Device.DNS.Client.Server.1.DNSServer",
    "dns_secondary": "Device.DNS.Client.Server.2.DNSServer",
    "vlan_id":       "Device.Ethernet.VLANTermination.1.VLANID",
}

# ──────────────────────────────────────────────
# Config → parameter dict helpers
# ──────────────────────────────────────────────

def wan_config_to_params(wan: dict) -> Dict[str, str]:
    params: Dict[str, str] = {}
    mode = wan.get("mode", "dhcp")
    if mode == "pppoe":
        for k, tr181 in WAN_PPPoE_PARAM_MAP.items():
            v = wan.get(k)
            if v:
                params[tr181] = str(v)
    elif mode == "static":
        for k, tr181 in WAN_STATIC_PARAM_MAP.items():
            v = wan.get(k)
            if v:
                params[tr181] = str(v)
    for k, tr181 in WAN_COMMON_PARAM_MAP.items():
        v = wan.get(k)
        if v:
            params[tr181] = str(v)
    return params


def wifi_config_to_params(wifi: dict, band: str) -> Dict[str, str]:
    mapping = WIFI_2G_PARAM_MAP if band == "2g" else WIFI_5G_PARAM_MAP
    params: Dict[str, str] = {}
    for k, tr181 in mapping.items():
        v = wifi.get(k)
        if v is None:
            continue
        if isinstance(v, bool):
            params[tr181] = "true" if v else "false"
        elif k == "channel" and str(v) == "auto":
            params[tr181] = "0"   # 0 = auto in TR-181
        elif k == "tx_power" and str(v) == "auto":
            params[tr181] = "0"
        else:
            params[tr181] = str(v)
    return params


# ──────────────────────────────────────────────
# Serialiser
# ──────────────────────────────────────────────

def _ser(t: dict) -> dict:
    t = dict(t)
    if "_id" in t:
        t["id"] = str(t.pop("_id"))
    return t


# ──────────────────────────────────────────────
# Task CRUD
# ──────────────────────────────────────────────

class TaskCreate(BaseModel):
    task_type: str
    parameters: Optional[Dict[str, str]] = None
    priority: int = 5
    label: Optional[str] = None


@router.get("/{device_id}/tasks")
async def list_tasks(
    device_id: str,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    query: dict = {"device_id": device_id}
    if status:
        query["status"] = status
    tasks = await db.cwmp_tasks.find(query).sort("created_at", -1).to_list(100)
    return [_ser(t) for t in tasks]


@router.post("/{device_id}/tasks")
async def create_task(
    device_id: str,
    data: TaskCreate,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot queue device tasks")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if data.task_type not in TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown task type. Use: {TASK_TYPES}")

    task = _build_task(device_id, device.get("serial_number", ""), data.task_type,
                       data.parameters or {}, data.priority,
                       data.label or data.task_type.replace("_", " ").title(),
                       current_user["id"])
    await db.cwmp_tasks.insert_one(task)
    return _ser(task)


@router.delete("/{device_id}/tasks/{task_id}")
async def cancel_task(
    device_id: str,
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot cancel tasks")
    task = await find_by_id(db.cwmp_tasks, task_id)
    if not task or task["device_id"] != device_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] not in ("pending",):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status: {task['status']}")
    await db.cwmp_tasks.update_one({"_id": task["_id"]}, {"$set": {"status": "cancelled"}})
    return {"message": "Task cancelled"}


# ──────────────────────────────────────────────
# Shortcut convenience endpoints
# ──────────────────────────────────────────────

@router.post("/{device_id}/tasks/push-wan")
async def push_wan_config(device_id: str, current_user: dict = Depends(get_current_user)):
    """Queue a SetParameterValues task from the device's current WAN config."""
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot push device config")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    params = wan_config_to_params(device.get("wan_config", {}))
    if not params:
        raise HTTPException(status_code=400, detail="No WAN parameters to push. Save a WAN config first.")

    task = _build_task(device_id, device.get("serial_number", ""),
                       "set_parameter_values", params, 5,
                       "Push WAN Config to Device", current_user["id"])
    await db.cwmp_tasks.insert_one(task)
    return _ser(task)


@router.post("/{device_id}/tasks/push-wifi-2g")
async def push_wifi_2g(device_id: str, current_user: dict = Depends(get_current_user)):
    """Queue SetParameterValues from the device's current 2.4 GHz WiFi config."""
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot push device config")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    params = wifi_config_to_params(device.get("wifi_config_2g", {}), "2g")
    if not params:
        raise HTTPException(status_code=400, detail="No 2.4 GHz WiFi parameters to push.")

    task = _build_task(device_id, device.get("serial_number", ""),
                       "set_parameter_values", params, 5,
                       "Push WiFi 2.4 GHz Config", current_user["id"])
    await db.cwmp_tasks.insert_one(task)
    return _ser(task)


@router.post("/{device_id}/tasks/push-wifi-5g")
async def push_wifi_5g(device_id: str, current_user: dict = Depends(get_current_user)):
    """Queue SetParameterValues from the device's current 5 GHz WiFi config."""
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot push device config")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    params = wifi_config_to_params(device.get("wifi_config_5g", {}), "5g")
    if not params:
        raise HTTPException(status_code=400, detail="No 5 GHz WiFi parameters to push.")

    task = _build_task(device_id, device.get("serial_number", ""),
                       "set_parameter_values", params, 5,
                       "Push WiFi 5 GHz Config", current_user["id"])
    await db.cwmp_tasks.insert_one(task)
    return _ser(task)


@router.post("/{device_id}/tasks/reboot")
async def reboot_device(device_id: str, current_user: dict = Depends(get_current_user)):
    """Queue a Reboot task for the device (executed on next Inform)."""
    db = get_db()
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Staff cannot reboot devices")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    task = _build_task(device_id, device.get("serial_number", ""),
                       "reboot", {}, 1,   # priority 1 = highest
                       "Reboot Device", current_user["id"])
    await db.cwmp_tasks.insert_one(task)
    return _ser(task)


@router.post("/{device_id}/tasks/factory-reset")
async def factory_reset_device(device_id: str, current_user: dict = Depends(get_current_user)):
    """Queue a FactoryReset task — USE WITH CAUTION."""
    db = get_db()
    if current_user["role"] not in ("super_admin", "operator"):
        raise HTTPException(status_code=403, detail="Only admin/operator can factory reset")
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] == "operator" and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    task = _build_task(device_id, device.get("serial_number", ""),
                       "factory_reset", {}, 1,
                       "Factory Reset Device", current_user["id"])
    await db.cwmp_tasks.insert_one(task)
    return _ser(task)


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _build_task(device_id: str, serial: str, task_type: str,
                parameters: dict, priority: int, label: str,
                created_by: str) -> dict:
    return {
        "_id": new_id(),
        "device_id": device_id,
        "serial_number": serial,
        "task_type": task_type,
        "parameters": parameters,
        "priority": priority,
        "label": label,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": created_by,
        "dispatched_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
