"""
ACS (Auto Configuration Server) endpoint supporting TR-069 (CWMP) and TR-369 (USP)
Multi-operator: Each operator has a unique acs_username/acs_password.
Routers set those credentials in their CWMP settings so devices auto-assign to the right operator.
"""
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import xml.etree.ElementTree as ET
import logging
import re
import base64

from database import get_db
from auth_utils import get_current_user
from utils import new_id
from crypto_utils import decrypt_value

router = APIRouter(prefix="/acs", tags=["acs"])
logger = logging.getLogger(__name__)

CWMP_NS = "urn:dslforum-org:cwmp-1-0"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
XSD_NS = "http://www.w3.org/2001/XMLSchema"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"


def parse_inform_xml(body: str) -> dict:
    """Parse TR-069 CWMP Inform SOAP message"""
    try:
        root = ET.fromstring(body)
        namespaces = {
            "soap": SOAP_NS,
            "cwmp": CWMP_NS,
        }
        inform = root.find(".//cwmp:Inform", namespaces) or root.find(".//{%s}Inform" % CWMP_NS)
        if inform is None:
            return {}

        device_id = inform.find("DeviceId") or inform.find("{%s}DeviceId" % CWMP_NS)
        result = {}
        if device_id is not None:
            result["manufacturer"] = (device_id.findtext("Manufacturer") or "").strip()
            result["oui"] = (device_id.findtext("OUI") or "").strip()
            result["product_class"] = (device_id.findtext("ProductClass") or "").strip()
            result["serial_number"] = (device_id.findtext("SerialNumber") or "").strip()

        params = {}
        param_list = inform.findall(".//ParameterValueStruct")
        for pv in param_list:
            name = pv.findtext("Name") or ""
            value = pv.findtext("Value") or ""
            params[name] = value

        # Extract common parameters
        for key, val in params.items():
            if "SoftwareVersion" in key or "FirmwareVersion" in key:
                result["firmware_version"] = val
            elif "ExternalIPAddress" in key or "WAN.IP" in key:
                result["ip_address"] = val
            elif "MACAddress" in key and "WAN" in key:
                result["mac_address"] = val
            elif "Uptime" in key and "Device" not in key:
                try:
                    result["uptime"] = int(val)
                except:
                    pass

        result["parameters"] = params
        return result
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return {}


def build_inform_response() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
  <SOAP-ENV:Header>
    <cwmp:ID mustUnderstand="1">1</cwmp:ID>
    <cwmp:NoMoreRequests>1</cwmp:NoMoreRequests>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <cwmp:InformResponse>
      <MaxEnvelopes>1</MaxEnvelopes>
    </cwmp:InformResponse>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


async def _resolve_operator_from_auth(request: Request, db) -> Optional[str]:
    """
    Parse HTTP Basic Auth from the router's CWMP request.
    Match acs_username + acs_password against the operators collection.
    Returns operator_id string if matched, None otherwise.
    Falls back to global ACS credentials check.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return None

    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        acs_user, acs_pass = decoded.split(":", 1)
    except Exception:
        return None

    # 1. Try per-operator credentials — query by username, then verify decrypted password
    op = await db.operators.find_one({
        "acs_username": acs_user,
        "is_active": True,
    })
    if op:
        stored_pass = decrypt_value(op.get("acs_password", ""))
        if stored_pass == acs_pass:
            logger.info(f"CWMP auth: matched operator '{op['name']}' ({op['code']})")
            return str(op["_id"])
        # Username matched but password wrong — fall through to reject
        logger.warning(f"CWMP auth: wrong password for operator '{op.get('name', acs_user)}'")
        return "UNAUTHORIZED"

    # 2. Fall back to global ACS credentials (for legacy / unassigned devices)
    settings = await db.settings.find_one({"_id": "global"})
    global_user = settings.get("acs_username", "acs") if settings else "acs"
    global_pass = settings.get("acs_password", "acs123") if settings else "acs123"
    if acs_user == global_user and acs_pass == global_pass:
        logger.info("CWMP auth: matched global fallback credentials (unassigned)")
        return None  # None = unassigned, but accepted

    # 3. No match at all — reject
    logger.warning(f"CWMP auth: unknown credentials user='{acs_user}'")
    return "UNAUTHORIZED"


@router.post("/cwmp")
async def cwmp_endpoint(request: Request):
    """TR-069 CWMP ACS endpoint — routers connect here.
    ACS Username in the router CWMP settings identifies the operator.
    """
    db = get_db()
    body = await request.body()
    body_str = body.decode("utf-8", errors="replace")

    # --- Multi-operator auth ---
    operator_id_result = await _resolve_operator_from_auth(request, db)
    if operator_id_result == "UNAUTHORIZED":
        return Response(
            content="Unauthorized",
            status_code=401,
            media_type="text/plain",
            headers={"WWW-Authenticate": 'Basic realm="ACS"'},
        )
    operator_id = operator_id_result  # None = global/unassigned, str = specific operator

    if not body_str.strip():
        return Response(content="", status_code=204)

    device_data = parse_inform_xml(body_str)
    if device_data.get("serial_number"):
        serial = device_data["serial_number"]
        existing = await db.devices.find_one({"serial_number": serial})
        now = datetime.now(timezone.utc).isoformat()

        if existing:
            update = {
                "status": "online",
                "last_seen": now,
                "protocol": "tr069",
            }
            if device_data.get("firmware_version"):
                update["firmware_version"] = device_data["firmware_version"]
            if device_data.get("ip_address"):
                update["ip_address"] = device_data["ip_address"]
            if device_data.get("uptime"):
                update["uptime"] = device_data["uptime"]
            # Auto-assign operator if device currently has none and we identified one
            if operator_id and not existing.get("operator_id"):
                update["operator_id"] = operator_id
                logger.info(f"CWMP: Auto-assigned existing device {serial} to operator {operator_id}")
            await db.devices.update_one({"serial_number": serial}, {"$set": update})
            logger.info(f"TR-069 Inform: Updated device {serial}")
        else:
            new_device = {
                "_id": new_id(),
                "name": f"{device_data.get('manufacturer', 'Unknown')} {device_data.get('product_class', serial)}",
                "serial_number": serial,
                "manufacturer": device_data.get("manufacturer", ""),
                "model": device_data.get("product_class", ""),
                "firmware_version": device_data.get("firmware_version", ""),
                "ip_address": device_data.get("ip_address", ""),
                "mac_address": device_data.get("mac_address", ""),
                "protocol": "tr069",
                "status": "online",
                "operator_id": operator_id,  # Auto-assigned from ACS credentials
                "last_seen": now,
                "created_at": now,
                "provision_code": serial[:8].upper(),
                "wan_config": {},
                "wifi_config_2g": {},
                "wifi_config_5g": {},
                "auto_discovered": True,
            }
            await db.devices.insert_one(new_device)
            op_info = f"operator {operator_id}" if operator_id else "unassigned"
            logger.info(f"TR-069 Inform: Auto-registered new device {serial} → {op_info}")

    return Response(
        content=build_inform_response(),
        media_type="text/xml; charset=utf-8",
        status_code=200
    )


class USPRegister(BaseModel):
    serial_number: str
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    ip_address: str = ""
    mac_address: str = ""
    endpoint_id: str = ""
    acs_username: str = ""   # operator acs_username for auto-assignment
    acs_password: str = ""


@router.post("/usp/register")
async def usp_register(data: USPRegister):
    """TR-369 USP device registration endpoint"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Resolve operator from credentials
    operator_id = None
    if data.acs_username and data.acs_password:
        op = await db.operators.find_one({
            "acs_username": data.acs_username,
            "acs_password": data.acs_password,
            "is_active": True,
        })
        if op:
            operator_id = str(op["_id"])

    existing = await db.devices.find_one({"serial_number": data.serial_number})

    if existing:
        update = {
            "status": "online",
            "last_seen": now,
            "protocol": "tr369",
        }
        for field in ["firmware_version", "ip_address", "mac_address"]:
            val = getattr(data, field, None)
            if val:
                update[field] = val
        if operator_id and not existing.get("operator_id"):
            update["operator_id"] = operator_id
        await db.devices.update_one({"serial_number": data.serial_number}, {"$set": update})
        return {"status": "updated", "serial": data.serial_number}
    else:
        new_device = {
            "_id": new_id(),
            "name": f"{data.manufacturer} {data.model or data.serial_number}",
            "serial_number": data.serial_number,
            "manufacturer": data.manufacturer,
            "model": data.model,
            "firmware_version": data.firmware_version,
            "ip_address": data.ip_address,
            "mac_address": data.mac_address,
            "endpoint_id": data.endpoint_id,
            "protocol": "tr369",
            "status": "online",
            "operator_id": operator_id,
            "last_seen": now,
            "created_at": now,
            "provision_code": data.serial_number[:8].upper(),
            "wan_config": {},
            "wifi_config_2g": {},
            "wifi_config_5g": {},
            "auto_discovered": True,
        }
        await db.devices.insert_one(new_device)
        return {"status": "registered", "serial": data.serial_number}


@router.get("/status")
async def acs_status(current_user: dict = Depends(get_current_user)):
    """ACS server status"""
    db = get_db()
    settings = await db.settings.find_one({"_id": "global"})
    total = await db.devices.count_documents({})
    online = await db.devices.count_documents({"status": "online"})
    return {
        "acs_running": True,
        "tr069_enabled": settings.get("tr069_enabled", True) if settings else True,
        "tr369_enabled": settings.get("tr369_enabled", True) if settings else True,
        "total_devices": total,
        "online_devices": online,
        "cwmp_endpoint": "/api/acs/cwmp",
        "usp_endpoint": "/api/acs/usp/register",
    }
