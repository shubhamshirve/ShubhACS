#!/usr/bin/env python3
"""
Extended Backend API Testing - Test real-time polling with actual device data
"""

import requests
import json

BASE_URL = "https://analyze-app-8.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@acsserver.com"
ADMIN_PASSWORD = "Admin@123"

session = requests.Session()

def print_test(name):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

# Login
print_test("Login")
response = session.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
if response.status_code == 200:
    print_success("Login successful")
else:
    print_error(f"Login failed: {response.status_code}")
    exit(1)

# Get or create an operator first
print_test("Get/Create Operator for Device")
operators_response = session.get(f"{BASE_URL}/operators")
if operators_response.status_code == 200:
    operators = operators_response.json()
    if len(operators) > 0:
        operator_id = operators[0]["id"]
        print_info(f"Using existing operator: {operator_id}")
    else:
        # Create operator
        op_data = {
            "name": "Test Operator",
            "code": "TESTOP",
            "contact_email": "test@operator.com"
        }
        op_response = session.post(f"{BASE_URL}/operators", json=op_data)
        if op_response.status_code == 200:
            operator_id = op_response.json()["id"]
            print_success(f"Created operator: {operator_id}")
        else:
            print_error(f"Failed to create operator: {op_response.status_code}")
            exit(1)
else:
    print_error(f"Failed to get operators: {operators_response.status_code}")
    exit(1)

# Create a test device
print_test("Create Test Device")
device_data = {
    "name": "Test Device for Polling",
    "serial_number": "TEST-POLL-001",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "ip_address": "192.168.1.100",
    "manufacturer": "Test Manufacturer",
    "model": "Test Model",
    "firmware_version": "1.0.0",
    "protocol": "tr069",
    "operator_id": operator_id,
    "location": "Test Location"
}

device_response = session.post(f"{BASE_URL}/devices", json=device_data)
if device_response.status_code == 200:
    device = device_response.json()
    device_id = device["id"]
    print_success(f"Created device: {device_id}")
    print_info(f"Device status: {device.get('status')}")
    print_info(f"Device IP: {device.get('ip_address')}")
else:
    print_error(f"Failed to create device: {device_response.status_code} - {device_response.text}")
    # Try to get existing devices
    devices_response = session.get(f"{BASE_URL}/devices")
    if devices_response.status_code == 200:
        devices = devices_response.json()
        if len(devices) > 0:
            device_id = devices[0]["id"]
            print_info(f"Using existing device: {device_id}")
        else:
            print_error("No devices available")
            exit(1)

# Test real-time polling endpoint with device data
print_test("Real-time Polling with Device Data")
polling_response = session.get(f"{BASE_URL}/devices/status-updates")

if polling_response.status_code == 200:
    print_success("✓ Endpoint returned 200 OK")
    
    data = polling_response.json()
    
    if isinstance(data, list):
        print_success(f"✓ Response is a JSON array")
        print_info(f"  Found {len(data)} devices")
        
        if len(data) > 0:
            # Check all devices have required fields
            all_valid = True
            required_fields = ["id", "status", "last_seen", "ip_address"]
            
            for i, device in enumerate(data):
                missing_fields = [f for f in required_fields if f not in device]
                
                if missing_fields:
                    print_error(f"✗ Device {i+1} missing fields: {missing_fields}")
                    all_valid = False
                else:
                    print_info(f"  Device {i+1}: id={device['id'][:8]}..., status={device['status']}, ip={device['ip_address']}")
            
            if all_valid:
                print_success(f"✓ All {len(data)} devices have required fields: {required_fields}")
                print_info(f"\nSample device data:")
                print(json.dumps(data[0], indent=2))
            else:
                print_error("✗ Some devices missing required fields")
        else:
            print_error("✗ No devices returned (expected at least 1)")
    else:
        print_error(f"✗ Response is not a JSON array: {type(data)}")
else:
    print_error(f"Endpoint failed: {polling_response.status_code} - {polling_response.text}")

print("\n" + "="*60)
print("EXTENDED TESTING COMPLETE")
print("="*60 + "\n")
