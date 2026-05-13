from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import subprocess
import random
import asyncio
import os

from database import get_db
from auth_utils import get_current_user
from utils import find_by_id, new_id

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def serialize(doc: dict) -> dict:
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def run_ping(host: str, count: int = 4) -> dict:
    if not host or host in ["", "0.0.0.0"]:
        return {"success": False, "error": "No valid IP address configured"}
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "2", host],
            capture_output=True, text=True, timeout=15
        )
        lines = result.stdout.strip().split("\n")
        stats = {"packets_sent": count, "packets_received": 0, "packet_loss": "100%", "rtt_min": 0, "rtt_avg": 0, "rtt_max": 0}
        for line in lines:
            if "packets transmitted" in line:
                parts = line.split(",")
                stats["packets_sent"] = int(parts[0].split()[0])
                stats["packets_received"] = int(parts[1].strip().split()[0])
                stats["packet_loss"] = parts[2].strip().split()[0]
            if "rtt min/avg/max" in line or "round-trip" in line:
                rtt_part = line.split("=")[-1].strip().split("/")
                stats["rtt_min"] = float(rtt_part[0])
                stats["rtt_avg"] = float(rtt_part[1])
                stats["rtt_max"] = float(rtt_part[2].split()[0])
        stats["raw_output"] = result.stdout
        stats["success"] = stats["packets_received"] > 0
        return stats
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Ping timed out", "raw_output": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_output": ""}


def run_traceroute(host: str) -> dict:
    if not host or host in ["", "0.0.0.0"]:
        return {"success": False, "error": "No valid IP address configured"}
    try:
        result = subprocess.run(
            ["traceroute", "-m", "10", "-w", "2", host],
            capture_output=True, text=True, timeout=30
        )
        hops = []
        for line in result.stdout.strip().split("\n")[1:]:
            parts = line.strip().split()
            if parts:
                hop = {"hop": parts[0], "host": "* * *", "rtt": []}
                for i, p in enumerate(parts[1:]):
                    if p not in ["ms", "*"] and "." in p:
                        hop["host"] = p
                    elif p != "ms" and p != "*":
                        try:
                            hop["rtt"].append(float(p))
                        except ValueError:
                            pass
                hops.append(hop)
        return {"success": True, "hops": hops, "raw_output": result.stdout, "hop_count": len(hops)}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Traceroute timed out", "raw_output": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_output": ""}


def simulate_speedtest() -> dict:
    download = round(random.uniform(20, 150), 2)
    upload = round(random.uniform(5, 50), 2)
    ping = round(random.uniform(5, 80), 1)
    jitter = round(random.uniform(1, 25), 1)
    return {
        "download_mbps": download,
        "upload_mbps": upload,
        "ping_ms": ping,
        "jitter_ms": jitter,
        "success": True,
        "server": "Speedtest Server - Mumbai",
        "isp": "ACS Test",
    }


@router.post("/{device_id}/ping")
async def ping_device(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    settings = await db.settings.find_one({"_id": "global"})
    if settings and not settings.get("diagnostics_enabled", True):
        raise HTTPException(status_code=400, detail="Diagnostics are disabled in global settings")

    ip = device.get("ip_address", "")
    result = await asyncio.to_thread(run_ping, ip)
    doc = {
        "_id": new_id(),
        "device_id": device_id,
        "type": "ping",
        "result": result,
        "ip_tested": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
    }
    await db.diagnostics.insert_one(doc)
    status_update = "online" if result.get("success") else "offline"
    await db.devices.update_one(
        {"_id": device["_id"]},
        {"$set": {"status": status_update, "last_seen": datetime.now(timezone.utc).isoformat()}}
    )
    return serialize(doc)


@router.post("/{device_id}/traceroute")
async def traceroute_device(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    settings = await db.settings.find_one({"_id": "global"})
    if settings and not settings.get("diagnostics_enabled", True):
        raise HTTPException(status_code=400, detail="Diagnostics are disabled")

    ip = device.get("ip_address", "")
    result = await asyncio.to_thread(run_traceroute, ip)
    doc = {
        "_id": new_id(),
        "device_id": device_id,
        "type": "traceroute",
        "result": result,
        "ip_tested": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
    }
    await db.diagnostics.insert_one(doc)
    return serialize(doc)


@router.post("/{device_id}/speedtest")
async def speedtest_device(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    settings = await db.settings.find_one({"_id": "global"})
    if settings and not settings.get("speed_test_enabled", True):
        raise HTTPException(status_code=400, detail="Speed test is disabled")

    await asyncio.sleep(2)
    result = simulate_speedtest()
    doc = {
        "_id": new_id(),
        "device_id": device_id,
        "type": "speedtest",
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
    }
    await db.diagnostics.insert_one(doc)
    return serialize(doc)


@router.post("/{device_id}/ai-analyze")
async def ai_analyze_device(device_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    settings = await db.settings.find_one({"_id": "global"})
    if not settings or not settings.get("ai_enabled", False):
        raise HTTPException(status_code=400, detail="AI diagnostics are disabled. Enable in Global Settings.")

    api_key = settings.get("gemini_api_key") or os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No AI API key configured")

    recent_diagnostics = await db.diagnostics.find(
        {"device_id": device_id}
    ).sort("created_at", -1).to_list(10)

    device_info = {
        "name": device.get("name"),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "firmware": device.get("firmware_version"),
        "protocol": device.get("protocol"),
        "status": device.get("status"),
        "ip_address": device.get("ip_address"),
        "wan_config": device.get("wan_config", {}),
        "last_seen": device.get("last_seen"),
    }
    diag_summary = []
    for d in recent_diagnostics:
        diag_summary.append({
            "type": d["type"],
            "result": d["result"],
            "time": d["created_at"]
        })

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid as _uuid

    chat = LlmChat(
        api_key=api_key,
        session_id=str(_uuid.uuid4()),
        system_message=(
            "You are an expert network engineer specializing in Indian ISP infrastructure and TR-069/TR-369 ACS management. "
            "Analyze router/CPE device diagnostics and provide clear, actionable insights. "
            "Format your response with sections: DEVICE STATUS, ISSUES DETECTED, RECOMMENDATIONS, and CONFIGURATION TIPS. "
            "Keep it concise but technical."
        )
    ).with_model("gemini", "gemini-3-flash-preview")

    prompt = f"""Analyze this CPE device and its recent diagnostics:

DEVICE INFO:
{device_info}

RECENT DIAGNOSTICS (last 10):
{diag_summary}

Provide a comprehensive diagnostic analysis with actionable recommendations."""

    response = await chat.send_message(UserMessage(text=prompt))

    doc = {
        "_id": new_id(),
        "device_id": device_id,
        "type": "ai_diagnostic",
        "result": {"analysis": response, "model": "gemini-3-flash-preview"},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
    }
    await db.diagnostics.insert_one(doc)
    return serialize(doc)


@router.get("/{device_id}/history")
async def get_diagnostic_history(
    device_id: str,
    diag_type: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    query = {"device_id": device_id}
    if diag_type:
        query["type"] = diag_type
    history = await db.diagnostics.find(query).sort("created_at", -1).to_list(limit)
    return [serialize(d) for d in history]
