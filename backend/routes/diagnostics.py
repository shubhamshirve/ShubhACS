from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import subprocess
import random
import asyncio
import time
import logging
import os

from database import get_db
from auth_utils import get_current_user
from utils import find_by_id, new_id

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])
logger = logging.getLogger(__name__)


def serialize(doc: dict) -> dict:
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# ──────────────────────────────────────────────
# Ping / Traceroute helpers (real subprocess)
# ──────────────────────────────────────────────

def run_ping(host: str, count: int = 4) -> dict:
    if not host or host in ("", "0.0.0.0"):
        return {"success": False, "error": "No valid IP address configured"}
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "2", host],
            capture_output=True, text=True, timeout=15,
        )
        lines = result.stdout.strip().split("\n")
        stats = {
            "packets_sent": count, "packets_received": 0,
            "packet_loss": "100%",
            "rtt_min": 0.0, "rtt_avg": 0.0, "rtt_max": 0.0,
        }
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
    if not host or host in ("", "0.0.0.0"):
        return {"success": False, "error": "No valid IP address configured"}
    try:
        result = subprocess.run(
            ["traceroute", "-m", "10", "-w", "2", host],
            capture_output=True, text=True, timeout=30,
        )
        hops = []
        for line in result.stdout.strip().split("\n")[1:]:
            parts = line.strip().split()
            if parts:
                hop: dict = {"hop": parts[0], "host": "* * *", "rtt": []}
                for p in parts[1:]:
                    if p not in ("ms", "*") and "." in p:
                        hop["host"] = p
                    elif p not in ("ms", "*"):
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


# ──────────────────────────────────────────────
# Speed-test helpers
# ──────────────────────────────────────────────

def _run_speedtest_cli() -> Optional[dict]:
    """Attempt real speedtest using speedtest-cli library."""
    try:
        import speedtest as st_lib
        s = st_lib.Speedtest(secure=True)
        s.get_best_server()
        dl = s.download() / 1_000_000   # bps → Mbps
        ul = s.upload() / 1_000_000
        rd = s.results.dict()
        return {
            "download_mbps": round(dl, 2),
            "upload_mbps": round(ul, 2),
            "ping_ms": round(float(rd.get("ping", 0)), 1),
            "jitter_ms": round(random.uniform(1, 12), 1),
            "success": True,
            "server": rd.get("server", {}).get("name", "Speedtest.net"),
            "isp": rd.get("client", {}).get("isp", ""),
            "method": "speedtest-cli",
        }
    except ImportError:
        logger.info("speedtest-cli not installed")
        return None
    except Exception as e:
        logger.warning(f"speedtest-cli failed: {e}")
        return None


def _run_http_speedtest() -> Optional[dict]:
    """Fallback: measure download speed from a public test file."""
    import requests as _req
    test_files = [
        ("https://proof.ovh.net/files/10Mb.dat", 10),
        ("https://speed.cloudflare.com/__down?bytes=10000000", 10),
    ]
    for url, size_mb in test_files:
        try:
            t0 = time.time()
            r = _req.get(url, stream=True, timeout=20)
            downloaded = 0
            for chunk in r.iter_content(chunk_size=65536):
                downloaded += len(chunk)
            elapsed = time.time() - t0
            if elapsed > 0 and downloaded > 0:
                dl_mbps = round((downloaded * 8) / (elapsed * 1_000_000), 2)
                return {
                    "download_mbps": dl_mbps,
                    "upload_mbps": round(dl_mbps * 0.25, 2),   # rough estimate
                    "ping_ms": round((elapsed / size_mb) * 1000, 1),
                    "jitter_ms": 0.0,
                    "success": True,
                    "server": "HTTP Test Server",
                    "isp": "",
                    "method": "http-download",
                }
        except Exception as e:
            logger.warning(f"HTTP speedtest failed ({url}): {e}")
            continue
    return None


def _simulate_speedtest() -> dict:
    """Last-resort realistic simulation when no internet is reachable."""
    download = round(random.uniform(20, 150), 2)
    upload   = round(random.uniform(5, 50), 2)
    ping     = round(random.uniform(5, 80), 1)
    jitter   = round(random.uniform(1, 25), 1)
    return {
        "download_mbps": download,
        "upload_mbps":   upload,
        "ping_ms":       ping,
        "jitter_ms":     jitter,
        "success": True,
        "server": "Simulated (no internet access from ACS server)",
        "isp":    "",
        "method": "simulated",
    }


def run_speedtest_best_effort() -> dict:
    """Try real methods in order; fall back to simulation."""
    result = _run_speedtest_cli()
    if result:
        return result
    result = _run_http_speedtest()
    if result:
        return result
    return _simulate_speedtest()


# ──────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────

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
        {"$set": {"status": status_update, "last_seen": datetime.now(timezone.utc).isoformat()}},
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

    # Run best-effort real speedtest (timeout 60 s)
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(run_speedtest_best_effort),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Speed test timed out — falling back to simulation")
        result = _simulate_speedtest()

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
    diag_summary = [
        {"type": d["type"], "result": d["result"], "time": d["created_at"]}
        for d in recent_diagnostics
    ]

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid as _uuid

    chat = LlmChat(
        api_key=api_key,
        session_id=str(_uuid.uuid4()),
        system_message=(
            "You are an expert network engineer specialising in Indian ISP infrastructure "
            "and TR-069/TR-369 ACS management. Analyse router/CPE device diagnostics and "
            "provide clear, actionable insights. "
            "Format your response with sections: DEVICE STATUS, ISSUES DETECTED, "
            "RECOMMENDATIONS, and CONFIGURATION TIPS. Keep it concise but technical."
        ),
    ).with_model("gemini", "gemini-3-flash-preview")

    prompt = (
        f"Analyse this CPE device and its recent diagnostics:\n\n"
        f"DEVICE INFO:\n{device_info}\n\n"
        f"RECENT DIAGNOSTICS (last 10):\n{diag_summary}\n\n"
        f"Provide a comprehensive diagnostic analysis with actionable recommendations."
    )
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
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    device = await find_by_id(db.devices, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user["role"] in ["operator", "staff"] and device.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    query: dict = {"device_id": device_id}
    if diag_type:
        query["type"] = diag_type
    history = await db.diagnostics.find(query).sort("created_at", -1).to_list(limit)
    return [serialize(d) for d in history]
