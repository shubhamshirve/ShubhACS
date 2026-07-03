#!/usr/bin/env python3
"""
Backend API Testing for ACS Server
Tests Task Queue, CWMP Session, and Real Speed Test
"""
import requests
import json
import time
from typing import Optional

# Configuration
BASE_URL = "https://82d4d32f-98ab-41f5-baa8-6f14a4e174fd.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@acsserver.com"
ADMIN_PASSWORD = "Admin@123"
TEST_DEVICE_ID = "420e874f-2fd9-49f3-b5ec-7ca52719ead2"
TEST_SERIAL = "SN123456"

# CWMP Auth for device
CWMP_AUTH = "Basic YWNzOmFjczEyMw=="  # acs:acs123

# Session for cookie-based auth
session = requests.Session()

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name: str, details: str = ""):
    print(f"✅ PASS: {test_name}")
    if details:
        print(f"   {details}")
    test_results["passed"].append(test_name)

def log_fail(test_name: str, details: str):
    print(f"❌ FAIL: {test_name}")
    print(f"   {details}")
    test_results["failed"].append(f"{test_name}: {details}")

def log_warning(test_name: str, details: str):
    print(f"⚠️  WARNING: {test_name}")
    print(f"   {details}")
    test_results["warnings"].append(f"{test_name}: {details}")

def login_admin() -> bool:
    """Login as admin using cookie-based auth"""
    print("\n=== Admin Login ===")
    try:
        resp = session.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            # Check if we got cookies
            if "access_token" in session.cookies:
                log_pass("Admin login", f"Logged in as {data.get('name', 'Admin')}")
                return True
            else:
                log_fail("Admin login", "No auth cookie received")
                return False
        else:
            log_fail("Admin login", f"Status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        log_fail("Admin login", f"Exception: {e}")
        return False

def test_task_queue():
    """Test Task Queue CRUD endpoints"""
    print("\n=== Task Queue Tests ===")
    
    # 1. List tasks (should work even if empty)
    try:
        resp = session.get(
            f"{BASE_URL}/devices/{TEST_DEVICE_ID}/tasks",
            timeout=10
        )
        if resp.status_code == 200:
            tasks = resp.json()
            log_pass("GET /devices/{id}/tasks", f"Returned {len(tasks)} tasks")
        else:
            log_fail("GET /devices/{id}/tasks", f"Status {resp.status_code}: {resp.text}")
            return
    except Exception as e:
        log_fail("GET /devices/{id}/tasks", f"Exception: {e}")
        return
    
    # 2. Queue a reboot task
    try:
        resp = session.post(
            f"{BASE_URL}/devices/{TEST_DEVICE_ID}/tasks/reboot",
            timeout=10
        )
        if resp.status_code == 200:
            task = resp.json()
            if task.get("status") == "pending" and task.get("task_type") == "reboot":
                log_pass("POST /devices/{id}/tasks/reboot", f"Task queued: {task.get('id')}")
                reboot_task_id = task.get("id")
            else:
                log_fail("POST /devices/{id}/tasks/reboot", f"Invalid task data: {task}")
                reboot_task_id = None
        else:
            log_fail("POST /devices/{id}/tasks/reboot", f"Status {resp.status_code}: {resp.text}")
            reboot_task_id = None
    except Exception as e:
        log_fail("POST /devices/{id}/tasks/reboot", f"Exception: {e}")
        reboot_task_id = None
    
    # 3. Save WAN config first (required for push-wan)
    try:
        wan_config = {
            "mode": "pppoe",
            "pppoe_username": "test@bsnl.in",
            "pppoe_password": "testpass123",
            "dns_primary": "8.8.8.8",
            "dns_secondary": "8.8.4.4"
        }
        resp = session.put(
            f"{BASE_URL}/devices/{TEST_DEVICE_ID}/wan",
            json=wan_config,
            timeout=10
        )
        if resp.status_code == 200:
            log_pass("PUT /devices/{id}/wan", "WAN config saved")
        else:
            log_warning("PUT /devices/{id}/wan", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_warning("PUT /devices/{id}/wan", f"Exception: {e}")
    
    # 4. Queue push-wan task
    try:
        resp = session.post(
            f"{BASE_URL}/devices/{TEST_DEVICE_ID}/tasks/push-wan",
            timeout=10
        )
        if resp.status_code == 200:
            task = resp.json()
            if task.get("status") == "pending" and task.get("task_type") == "set_parameter_values":
                params = task.get("parameters", {})
                if len(params) > 0:
                    log_pass("POST /devices/{id}/tasks/push-wan", 
                            f"Task queued with {len(params)} parameters")
                else:
                    log_fail("POST /devices/{id}/tasks/push-wan", "No parameters in task")
            else:
                log_fail("POST /devices/{id}/tasks/push-wan", f"Invalid task: {task}")
        else:
            log_fail("POST /devices/{id}/tasks/push-wan", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_fail("POST /devices/{id}/tasks/push-wan", f"Exception: {e}")
    
    # 5. Save WiFi 2.4G config first
    try:
        wifi_config = {
            "ssid": "TestNet24",
            "password": "test1234",
            "security": "WPA2",
            "channel": 6,
            "bandwidth": "20MHz",
            "enabled": True
        }
        resp = session.put(
            f"{BASE_URL}/devices/{TEST_DEVICE_ID}/wifi?band=2.4GHz",
            json=wifi_config,
            timeout=10
        )
        if resp.status_code == 200:
            log_pass("PUT /devices/{id}/wifi?band=2.4GHz", "WiFi 2.4G config saved")
        else:
            log_warning("PUT /devices/{id}/wifi?band=2.4GHz", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_warning("PUT /devices/{id}/wifi?band=2.4GHz", f"Exception: {e}")
    
    # 6. Queue push-wifi-2g task
    try:
        resp = session.post(
            f"{BASE_URL}/devices/{TEST_DEVICE_ID}/tasks/push-wifi-2g",
            timeout=10
        )
        if resp.status_code == 200:
            task = resp.json()
            if task.get("status") == "pending" and task.get("task_type") == "set_parameter_values":
                params = task.get("parameters", {})
                if len(params) > 0:
                    log_pass("POST /devices/{id}/tasks/push-wifi-2g", 
                            f"Task queued with {len(params)} parameters")
                else:
                    log_fail("POST /devices/{id}/tasks/push-wifi-2g", "No parameters in task")
            else:
                log_fail("POST /devices/{id}/tasks/push-wifi-2g", f"Invalid task: {task}")
        else:
            log_fail("POST /devices/{id}/tasks/push-wifi-2g", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_fail("POST /devices/{id}/tasks/push-wifi-2g", f"Exception: {e}")
    
    # 7. Cancel a task (if we have reboot_task_id)
    if reboot_task_id:
        try:
            resp = session.delete(
                f"{BASE_URL}/devices/{TEST_DEVICE_ID}/tasks/{reboot_task_id}",
                timeout=10
            )
            if resp.status_code == 200:
                log_pass("DELETE /devices/{id}/tasks/{task_id}", "Task cancelled")
            else:
                log_fail("DELETE /devices/{id}/tasks/{task_id}", 
                        f"Status {resp.status_code}: {resp.text}")
        except Exception as e:
            log_fail("DELETE /devices/{id}/tasks/{task_id}", f"Exception: {e}")

def test_cwmp_session():
    """Test CWMP Session with task dispatch"""
    print("\n=== CWMP Session Tests ===")
    headers = {
        "Authorization": CWMP_AUTH,
        "Content-Type": "text/xml; charset=utf-8"
    }
    
    # Inform XML
    inform_xml = """<?xml version="1.0"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-0"><SOAP-ENV:Body><cwmp:Inform><DeviceId><Manufacturer>Huawei</Manufacturer><OUI>00E0FC</OUI><ProductClass>HG8245H</ProductClass><SerialNumber>SN123456</SerialNumber></DeviceId><Event></Event><CurrentTime>2025-07-02T19:00:00Z</CurrentTime><RetryCount>0</RetryCount><ParameterList><ParameterValueStruct><Name>Device.DeviceInfo.SoftwareVersion</Name><Value>V3R016C10S100</Value></ParameterValueStruct></ParameterList></cwmp:Inform></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
    
    # Step 1: Send Inform
    try:
        resp = requests.post(
            f"{BASE_URL}/acs/cwmp",
            headers=headers,
            data=inform_xml,
            timeout=10
        )
        if resp.status_code == 200:
            if "InformResponse" in resp.text:
                log_pass("CWMP Inform → InformResponse", "Session established")
            else:
                log_fail("CWMP Inform → InformResponse", f"Unexpected response: {resp.text[:200]}")
                return
        else:
            log_fail("CWMP Inform → InformResponse", f"Status {resp.status_code}: {resp.text}")
            return
    except Exception as e:
        log_fail("CWMP Inform → InformResponse", f"Exception: {e}")
        return
    
    # Step 2: Send empty POST (device ready for commands)
    try:
        resp = requests.post(
            f"{BASE_URL}/acs/cwmp",
            headers=headers,
            data="",
            timeout=10
        )
        if resp.status_code == 200:
            response_text = resp.text
            # Check if we got a task dispatch (SetParameterValues or Reboot)
            if "SetParameterValues" in response_text or "Reboot" in response_text:
                if "SetParameterValues" in response_text:
                    log_pass("CWMP Empty POST → Task Dispatch", "SetParameterValues dispatched")
                else:
                    log_pass("CWMP Empty POST → Task Dispatch", "Reboot dispatched")
                
                # Step 3: Send task response
                if "SetParameterValues" in response_text:
                    response_xml = """<?xml version="1.0"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-0"><SOAP-ENV:Body><cwmp:SetParameterValuesResponse><Status>0</Status></cwmp:SetParameterValuesResponse></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
                else:
                    response_xml = """<?xml version="1.0"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:cwmp="urn:dslforum-org:cwmp-1-0"><SOAP-ENV:Body><cwmp:RebootResponse><Status>0</Status></cwmp:RebootResponse></SOAP-ENV:Body></SOAP-ENV:Envelope>"""
                
                try:
                    resp = requests.post(
                        f"{BASE_URL}/acs/cwmp",
                        headers=headers,
                        data=response_xml,
                        timeout=10
                    )
                    if resp.status_code == 200:
                        log_pass("CWMP Task Response → Complete", "Task marked completed")
                    else:
                        log_fail("CWMP Task Response → Complete", 
                                f"Status {resp.status_code}: {resp.text}")
                except Exception as e:
                    log_fail("CWMP Task Response → Complete", f"Exception: {e}")
            else:
                log_warning("CWMP Empty POST → Task Dispatch", 
                           "No tasks dispatched (queue may be empty)")
        else:
            log_fail("CWMP Empty POST → Task Dispatch", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_fail("CWMP Empty POST → Task Dispatch", f"Exception: {e}")

def test_real_speedtest():
    """Test Real Speed Test"""
    print("\n=== Real Speed Test ===")
    
    try:
        print("Running speed test (may take up to 60 seconds)...")
        start_time = time.time()
        resp = session.post(
            f"{BASE_URL}/diagnostics/{TEST_DEVICE_ID}/speedtest",
            timeout=65  # Allow 65s for 60s backend timeout
        )
        elapsed = time.time() - start_time
        
        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result", {})
            
            download = result.get("download_mbps", 0)
            upload = result.get("upload_mbps", 0)
            ping = result.get("ping_ms", 0)
            method = result.get("method", "unknown")
            
            if download > 0 and upload > 0 and ping > 0:
                log_pass("POST /diagnostics/{id}/speedtest", 
                        f"Download: {download} Mbps, Upload: {upload} Mbps, Ping: {ping} ms")
                
                # Check if it's a real test (not simulated)
                if method == "simulated":
                    log_warning("Speed test method", 
                               "Method is 'simulated' - no internet access from ACS server")
                elif method in ("speedtest-cli", "http-download"):
                    log_pass("Speed test method", f"Real test using: {method}")
                else:
                    log_warning("Speed test method", f"Unknown method: {method}")
            else:
                log_fail("POST /diagnostics/{id}/speedtest", 
                        f"Invalid results: download={download}, upload={upload}, ping={ping}")
        else:
            log_fail("POST /diagnostics/{id}/speedtest", 
                    f"Status {resp.status_code}: {resp.text}")
    except requests.Timeout:
        log_fail("POST /diagnostics/{id}/speedtest", "Request timed out after 65 seconds")
    except Exception as e:
        log_fail("POST /diagnostics/{id}/speedtest", f"Exception: {e}")

def test_acs_status():
    """Test ACS Status endpoint"""
    print("\n=== ACS Status Test ===")
    
    try:
        resp = session.get(
            f"{BASE_URL}/acs/status",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if "pending_tasks" in data and "dispatched_tasks" in data:
                log_pass("GET /acs/status", 
                        f"Pending: {data['pending_tasks']}, Dispatched: {data['dispatched_tasks']}")
            else:
                log_fail("GET /acs/status", 
                        f"Missing required fields: {list(data.keys())}")
        else:
            log_fail("GET /acs/status", f"Status {resp.status_code}: {resp.text}")
    except Exception as e:
        log_fail("GET /acs/status", f"Exception: {e}")

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results['failed']:
        print("\nFailed Tests:")
        for fail in test_results['failed']:
            print(f"  - {fail}")
    
    if test_results['warnings']:
        print("\nWarnings:")
        for warn in test_results['warnings']:
            print(f"  - {warn}")
    
    print("="*60)

def main():
    print("="*60)
    print("ACS Server Backend Testing")
    print("="*60)
    
    # Login
    if not login_admin():
        print("\n❌ Cannot proceed without admin authentication")
        return
    
    # Run tests
    test_task_queue()
    test_cwmp_session()
    test_real_speedtest()
    test_acs_status()
    
    # Summary
    print_summary()

if __name__ == "__main__":
    main()
