"""
ACS (Auto Configuration Server) — TR-069 CWMP + TR-369 USP
Full CWMP session handling with task-queue dispatch.

Session flow:
  1. Device POSTs Inform  → ACS returns InformResponse, stores session
  2. Device POSTs empty   → ACS dispatches next pending task (SetParameterValues / Reboot)
  3. Device POSTs result  → ACS marks task complete, dispatches next or closes session
  4. Device POSTs Fault   → ACS marks task failed, closes session
"""
import hashlib
import time
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import logging
import re
import base64
from typing import Dict, Optional

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone

from database import get_db
from auth_utils import get_current_user
from utils import new_id, find_by_id
from crypto_utils import decrypt_value

router = APIRouter(prefix="/acs", tags=["acs"])
logger = logging.getLogger(__name__)

CWMP_NS = "urn:dslforum-org:cwmp-1-0"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"

# ──────────────────────────────────────────────────────────────
# In-memory CWMP session store
# Key  : MD5(client_ip + ":" + auth_header)
# Value: {serial, device_id, dispatched_task_id, expires}
# ──────────────────────────────────────────────────────────────
_cwmp_sessions: Dict[str, dict] = {}
SESSION_TTL = 120   # seconds


def _session_key(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    auth = request.headers.get("Authorization", "")
    return hashlib.md5(f"{ip}:{auth}".encode()).hexdigest()


def _cleanup():
    now = time.time()
    expired = [k for k, v in _cwmp_sessions.items() if v.get("expires", 0) < now]
    for k in expired:
        del _cwmp_sessions[k]


# ──────────────────────────────────────────────────────────────
# Message-type detection
# ──────────────────────────────────────────────────────────────

def _msg_type(body: str) -> str:
    if not body.strip():
        return "empty"
    if "Inform>" in body:
        return "inform"
    if "SetParameterValuesResponse" in body:
        return "spv_response"
    if "GetParameterValuesResponse" in body:
        return "gpv_response"
    if "RebootResponse" in body:
        return "reboot_response"
    if "FactoryResetResponse" in body:
        return "factory_reset_response"
    if "TransferComplete" in body:
        return "transfer_complete"
    if "Fault>" in body or "<faultcode>" in body.lower():
        return "fault"
    return "unknown"


def _extract_fault(body: str) -> str:
    try:
        root = ET.fromstring(body)
        for fault in root.iter():
            if fault.tag.endswith("Fault"):
                code = fault.findtext("FaultCode") or fault.findtext("{%s}FaultCode" % CWMP_NS) or ""
                string = fault.findtext("FaultString") or fault.findtext("{%s}FaultString" % CWMP_NS) or ""
                if code:
                    return f"Code {code}: {string}"
    except Exception:
        pass
    return "Fault received from device"


# ──────────────────────────────────────────────────────────────
# SOAP XML builders
# ──────────────────────────────────────────────────────────────

def _build_inform_response() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
  <SOAP-ENV:Header>
    <cwmp:ID mustUnderstand="1">1</cwmp:ID>
    <cwmp:NoMoreRequests>0</cwmp:NoMoreRequests>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <cwmp:InformResponse>
      <MaxEnvelopes>1</MaxEnvelopes>
    </cwmp:InformResponse>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


def _build_empty() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
  <SOAP-ENV:Header>
    <cwmp:ID mustUnderstand="1">0</cwmp:ID>
    <cwmp:NoMoreRequests>1</cwmp:NoMoreRequests>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body/>
</SOAP-ENV:Envelope>"""


def _build_spv(parameters: dict, task_id: str) -> str:
    """Build a SetParameterValues SOAP envelope."""
    structs = ""
    for name, value in parameters.items():
        xsi_type = "xsd:string"
        v = str(value)
        if v.lower() in ("true", "false"):
            xsi_type = "xsd:boolean"
        elif v.isdigit():
            xsi_type = "xsd:unsignedInt"
        structs += (
            f"        <ParameterValueStruct>\n"
            f"          <Name>{saxutils.escape(name)}</Name>\n"
            f"          <Value xsi:type=\"{xsi_type}\">{saxutils.escape(v)}</Value>\n"
            f"        </ParameterValueStruct>\n"
        )
    count = len(parameters)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/">
  <SOAP-ENV:Header>
    <cwmp:ID mustUnderstand="1">ACS0001</cwmp:ID>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <cwmp:SetParameterValues>
      <ParameterList soap-enc:arrayType="cwmp:ParameterValueStruct[{count}]">
{structs}      </ParameterList>
      <ParameterKey>task-{task_id}</ParameterKey>
    </cwmp:SetParameterValues>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


def _build_reboot(task_id: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
  <SOAP-ENV:Header>
    <cwmp:ID mustUnderstand="1">ACS0002</cwmp:ID>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <cwmp:Reboot>
      <CommandKey>task-{task_id}</CommandKey>
    </cwmp:Reboot>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


def _build_factory_reset(task_id: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:cwmp="urn:dslforum-org:cwmp-1-0">
  <SOAP-ENV:Header>
    <cwmp:ID mustUnderstand="1">ACS0003</cwmp:ID>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <cwmp:FactoryReset>
      <CommandKey>task-{task_id}</CommandKey>
    </cwmp:FactoryReset>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


# ──────────────────────────────────────────────────────────────
# TR-069 Inform XML parser (unchanged from original)
# ──────────────────────────────────────────────────────────────

def parse_inform_xml(body: str) -> dict:
    """Parse TR-069 Inform SOAP body. Falls back to regex if XML is malformed."""
    # Pre-process: strip undeclared namespace attributes that trip up strict XML parsers
    body_clean = re.sub(r'\s+[\w-]+:[\w-]+=(?:"[^"]*"|\'[^\']*\')', lambda m: (
        m.group(0) if any(
            m.group(0).startswith(f' {pfx}:') and f'xmlns:{pfx}=' in body
            for pfx in re.findall(r' ([\w-]+):[\w-]+=', m.group(0))
        ) else ''
    ), body)
    try:
        root = ET.fromstring(body_clean)
        namespaces = {"soap": SOAP_NS, "cwmp": CWMP_NS}
        inform = (root.find(".//cwmp:Inform", namespaces)
                  or root.find(".//{%s}Inform" % CWMP_NS))
        if inform is None:
            return {}

        device_id_el = inform.find("DeviceId") or inform.find("{%s}DeviceId" % CWMP_NS)
        result: dict = {}
        if device_id_el is not None:
            result["manufacturer"]  = (device_id_el.findtext("Manufacturer") or "").strip()
            result["oui"]           = (device_id_el.findtext("OUI") or "").strip()
            result["product_class"] = (device_id_el.findtext("ProductClass") or "").strip()
            result["serial_number"] = (device_id_el.findtext("SerialNumber") or "").strip()

        params: dict = {}
        for pv in inform.findall(".//ParameterValueStruct"):
            name  = pv.findtext("Name")  or ""
            value = pv.findtext("Value") or ""
            params[name] = value

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
                except Exception:
                    pass

        result["parameters"] = params
        return result
    except ET.ParseError as e:
        logger.warning(f"XML parse error (trying regex fallback): {e}")

    # Regex fallback for strictly non-conformant XML
    result: dict = {}
    m = re.search(r"<SerialNumber>([^<]+)</SerialNumber>", body)
    if m:
        result["serial_number"] = m.group(1).strip()
    m = re.search(r"<Manufacturer>([^<]+)</Manufacturer>", body)
    if m:
        result["manufacturer"] = m.group(1).strip()
    m = re.search(r"<ProductClass>([^<]+)</ProductClass>", body)
    if m:
        result["product_class"] = m.group(1).strip()
    m = re.search(r"<OUI>([^<]+)</OUI>", body)
    if m:
        result["oui"] = m.group(1).strip()
    # Extract version parameters
    for param_name, param_val in re.findall(r"<Name>([^<]+)</Name>\s*<Value[^>]*>([^<]*)</Value>", body):
        if "SoftwareVersion" in param_name or "FirmwareVersion" in param_name:
            result["firmware_version"] = param_val
        elif "ExternalIPAddress" in param_name:
            result["ip_address"] = param_val
    logger.info(f"Regex fallback extracted: serial={result.get('serial_number')!r}")
    return result


# ──────────────────────────────────────────────────────────────
# Operator auth helper (unchanged)
# ──────────────────────────────────────────────────────────────

async def _resolve_operator_from_auth(request: Request, db) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        acs_user, acs_pass = decoded.split(":", 1)
    except Exception:
        return None

    op = await db.operators.find_one({"acs_username": acs_user, "is_active": True})
    if op:
        stored_pass = decrypt_value(op.get("acs_password", ""))
        if stored_pass == acs_pass:
            logger.info(f"CWMP auth: matched operator '{op['name']}' ({op['code']})")
            return str(op["_id"])
        logger.warning(f"CWMP auth: wrong password for operator '{op.get('name', acs_user)}'")
        return "UNAUTHORIZED"

    settings = await db.settings.find_one({"_id": "global"})
    global_user = settings.get("acs_username", "acs") if settings else "acs"
    global_pass = settings.get("acs_password", "acs123") if settings else "acs123"
    if acs_user == global_user and acs_pass == global_pass:
        logger.info("CWMP auth: matched global fallback (unassigned)")
        return None

    logger.warning(f"CWMP auth: unknown credentials user='{acs_user}'")
    return "UNAUTHORIZED"


# ──────────────────────────────────────────────────────────────
# Task dispatch helper
# ──────────────────────────────────────────────────────────────

async def _dispatch_next_task(db, device_id: str, session: dict) -> Optional[Response]:
    """Find the next pending task for this device and return a SOAP Response.
    Returns None if there are no pending tasks (caller should close session)."""
    task = await db.cwmp_tasks.find_one(
        {"device_id": device_id, "status": "pending"},
        sort=[("priority", 1), ("created_at", 1)],
    )
    if not task:
        return None

    task_id = str(task["_id"])
    task_type = task["task_type"]
    now = datetime.now(timezone.utc).isoformat()

    await db.cwmp_tasks.update_one(
        {"_id": task["_id"]},
        {"$set": {"status": "dispatched", "dispatched_at": now}},
    )
    session["dispatched_task_id"] = task_id
    session["dispatched_task_type"] = task_type
    logger.info(f"CWMP: dispatching task {task_id} ({task_type}) → device {device_id}")

    if task_type == "reboot":
        soap = _build_reboot(task_id)
    elif task_type == "factory_reset":
        soap = _build_factory_reset(task_id)
    else:   # set_parameter_values + any custom task with parameters
        params = task.get("parameters") or {}
        if not params:
            # Nothing to send — mark complete immediately
            await db.cwmp_tasks.update_one(
                {"_id": task["_id"]},
                {"$set": {"status": "completed", "completed_at": now,
                           "result": {"message": "No parameters — auto-completed"}}},
            )
            session["dispatched_task_id"] = None
            return await _dispatch_next_task(db, device_id, session)
        soap = _build_spv(params, task_id)

    return Response(content=soap, media_type="text/xml; charset=utf-8", status_code=200)


# ──────────────────────────────────────────────────────────────
# Main CWMP endpoint
# ──────────────────────────────────────────────────────────────

@router.post("/cwmp")
async def cwmp_endpoint(request: Request):
    """TR-069 CWMP ACS endpoint — full session lifecycle with task-queue."""
    db = get_db()
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8", errors="replace")

    # ── Auth ──
    op_result = await _resolve_operator_from_auth(request, db)
    if op_result == "UNAUTHORIZED":
        return Response(
            content="Unauthorized", status_code=401, media_type="text/plain",
            headers={"WWW-Authenticate": 'Basic realm="ACS"'},
        )
    operator_id = op_result

    skey = _session_key(request)
    _cleanup()
    mtype = _msg_type(body)
    logger.info(f"CWMP [{skey[:8]}] msg_type={mtype}")

    # ──────────────────────────────────────────
    # 1. INFORM — register/update device
    # ──────────────────────────────────────────
    if mtype == "inform":
        device_data = parse_inform_xml(body)
        serial = device_data.get("serial_number", "")
        device_id = None

        if serial:
            existing = await db.devices.find_one({"serial_number": serial})
            now = datetime.now(timezone.utc).isoformat()

            if existing:
                upd = {"status": "online", "last_seen": now, "protocol": "tr069"}
                for f in ("firmware_version", "ip_address", "mac_address", "uptime"):
                    if device_data.get(f):
                        upd[f] = device_data[f]
                if operator_id and not existing.get("operator_id"):
                    upd["operator_id"] = operator_id
                    logger.info(f"CWMP: auto-assigned {serial} → operator {operator_id}")
                await db.devices.update_one({"serial_number": serial}, {"$set": upd})
                device_id = str(existing["_id"])
            else:
                new_dev = {
                    "_id": new_id(),
                    "name": f"{device_data.get('manufacturer', 'Unknown')} "
                            f"{device_data.get('product_class', serial)}",
                    "serial_number": serial,
                    "manufacturer": device_data.get("manufacturer", ""),
                    "model": device_data.get("product_class", ""),
                    "firmware_version": device_data.get("firmware_version", ""),
                    "ip_address": device_data.get("ip_address", ""),
                    "mac_address": device_data.get("mac_address", ""),
                    "protocol": "tr069",
                    "status": "online",
                    "operator_id": operator_id,
                    "last_seen": now,
                    "created_at": now,
                    "provision_code": serial[:8].upper(),
                    "wan_config": {},
                    "wifi_config_2g": {},
                    "wifi_config_5g": {},
                    "auto_discovered": True,
                }
                await db.devices.insert_one(new_dev)
                device_id = str(new_dev["_id"])
                logger.info(f"CWMP: auto-registered device {serial}")

        # Store session so next empty POST can dispatch tasks
        _cwmp_sessions[skey] = {
            "serial": serial,
            "device_id": device_id,
            "dispatched_task_id": None,
            "dispatched_task_type": None,
            "expires": time.time() + SESSION_TTL,
        }
        # Respond with InformResponse; device will POST empty to signal readiness
        return Response(
            content=_build_inform_response(),
            media_type="text/xml; charset=utf-8",
            status_code=200,
        )

    # ──────────────────────────────────────────
    # 2. EMPTY — device ready for ACS commands
    # ──────────────────────────────────────────
    elif mtype == "empty":
        session = _cwmp_sessions.get(skey)
        if not session or not session.get("device_id"):
            return Response(content=_build_empty(), media_type="text/xml", status_code=200)

        resp = await _dispatch_next_task(db, session["device_id"], session)
        if resp:
            return resp
        # No pending tasks — close session
        return Response(content=_build_empty(), media_type="text/xml", status_code=200)

    # ──────────────────────────────────────────
    # 3. TASK RESPONSE — mark task done, maybe dispatch next
    # ──────────────────────────────────────────
    elif mtype in ("spv_response", "gpv_response", "reboot_response",
                   "factory_reset_response", "transfer_complete"):
        session = _cwmp_sessions.get(skey)
        now = datetime.now(timezone.utc).isoformat()

        if session and session.get("dispatched_task_id"):
            task_id = session["dispatched_task_id"]
            task = await find_by_id(db.cwmp_tasks, task_id)
            if task:
                is_fault = "Fault>" in body
                status = "failed" if is_fault else "completed"
                result_info: dict = {"timestamp": now, "response_type": mtype}
                if is_fault:
                    result_info["fault"] = _extract_fault(body)
                await db.cwmp_tasks.update_one(
                    {"_id": task["_id"]},
                    {"$set": {"status": status, "completed_at": now,
                               "result": result_info,
                               "error": result_info.get("fault")}},
                )
                logger.info(f"CWMP: task {task_id} → {status}")
            session["dispatched_task_id"] = None
            session["dispatched_task_type"] = None

        # Dispatch next if any
        if session and session.get("device_id"):
            resp = await _dispatch_next_task(db, session["device_id"], session)
            if resp:
                return resp

        return Response(content=_build_empty(), media_type="text/xml", status_code=200)

    # ──────────────────────────────────────────
    # 4. FAULT — device reported error
    # ──────────────────────────────────────────
    elif mtype == "fault":
        session = _cwmp_sessions.get(skey)
        if session and session.get("dispatched_task_id"):
            task_id = session["dispatched_task_id"]
            task = await find_by_id(db.cwmp_tasks, task_id)
            if task:
                await db.cwmp_tasks.update_one(
                    {"_id": task["_id"]},
                    {"$set": {
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "error": _extract_fault(body),
                    }},
                )
            if session:
                session["dispatched_task_id"] = None
        return Response(content=_build_empty(), media_type="text/xml", status_code=200)

    # ── Unknown / unhandled ──
    return Response(content=_build_empty(), media_type="text/xml", status_code=200)


# ──────────────────────────────────────────────────────────────
# TR-369 USP — unchanged
# ──────────────────────────────────────────────────────────────

class USPRegister(BaseModel):
    serial_number: str
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    ip_address: str = ""
    mac_address: str = ""
    endpoint_id: str = ""
    acs_username: str = ""
    acs_password: str = ""


@router.post("/usp/register")
async def usp_register(data: USPRegister):
    """TR-369 USP device registration endpoint."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

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
        upd = {"status": "online", "last_seen": now, "protocol": "tr369"}
        for f in ("firmware_version", "ip_address", "mac_address"):
            v = getattr(data, f, None)
            if v:
                upd[f] = v
        if operator_id and not existing.get("operator_id"):
            upd["operator_id"] = operator_id
        await db.devices.update_one({"serial_number": data.serial_number}, {"$set": upd})
        return {"status": "updated", "serial": data.serial_number}
    else:
        new_dev = {
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
        await db.devices.insert_one(new_dev)
        return {"status": "registered", "serial": data.serial_number}


# ──────────────────────────────────────────────────────────────
# ACS status (unchanged)
# ──────────────────────────────────────────────────────────────

@router.get("/status")
async def acs_status(current_user: dict = Depends(get_current_user)):
    db = get_db()
    settings = await db.settings.find_one({"_id": "global"})
    total = await db.devices.count_documents({})
    online = await db.devices.count_documents({"status": "online"})
    pending_tasks = await db.cwmp_tasks.count_documents({"status": "pending"})
    dispatched_tasks = await db.cwmp_tasks.count_documents({"status": "dispatched"})
    return {
        "acs_running": True,
        "tr069_enabled": settings.get("tr069_enabled", True) if settings else True,
        "tr369_enabled": settings.get("tr369_enabled", True) if settings else True,
        "total_devices": total,
        "online_devices": online,
        "cwmp_endpoint": "/api/acs/cwmp",
        "usp_endpoint": "/api/acs/usp/register",
        "pending_tasks": pending_tasks,
        "dispatched_tasks": dispatched_tasks,
    }
