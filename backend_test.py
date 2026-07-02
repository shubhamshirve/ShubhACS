#!/usr/bin/env python3
"""
Backend API Testing Script for ACS Server
Tests UUID migration and real-time polling endpoints
"""

import requests
import json
import re
import sys
import os

# Get base URL from environment
BASE_URL = "https://tr069-config.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@acsserver.com"
ADMIN_PASSWORD = "Admin@123"

# Session for cookie-based auth
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

def is_uuid(value):
    """Check if value is a valid UUID string (36 chars with dashes)"""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, str(value), re.IGNORECASE))

def is_objectid(value):
    """Check if value is a valid MongoDB ObjectId (24 hex chars)"""
    objectid_pattern = r'^[0-9a-f]{24}$'
    return bool(re.match(objectid_pattern, str(value), re.IGNORECASE))

def login():
    """Login and establish session"""
    print_test("Authentication - Login")
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Login successful: {data.get('email')} ({data.get('role')})")
        return True
    else:
        print_error(f"Login failed: {response.status_code} - {response.text}")
        return False

def test_uuid_migration():
    """Test UUID migration for new records"""
    print_test("UUID Migration - Create New Operator")
    
    # Create a new operator
    operator_data = {
        "name": "Test Operator UUID",
        "code": "TESTUUID",
        "contact_email": "test@uuid.com",
        "contact_phone": "+1234567890",
        "address": "123 Test Street",
        "is_active": True
    }
    
    response = session.post(f"{BASE_URL}/operators", json=operator_data)
    
    if response.status_code == 200:
        operator = response.json()
        operator_id = operator.get("id")
        
        print_info(f"Created operator ID: {operator_id}")
        
        # Check if ID is UUID format
        if is_uuid(operator_id):
            print_success(f"✓ Operator ID is UUID format (36 chars with dashes)")
            print_info(f"  Length: {len(operator_id)} chars")
            return operator_id
        else:
            print_error(f"✗ Operator ID is NOT UUID format: {operator_id}")
            print_info(f"  Length: {len(operator_id)} chars")
            return None
    else:
        print_error(f"Failed to create operator: {response.status_code} - {response.text}")
        return None

def test_legacy_objectid_compatibility():
    """Test backward compatibility with legacy ObjectId records"""
    print_test("UUID Migration - Legacy ObjectId Compatibility")
    
    # Get all router models (may contain legacy ObjectId records)
    response = session.get(f"{BASE_URL}/router-models")
    
    if response.status_code == 200:
        models = response.json()
        print_info(f"Found {len(models)} router models")
        
        if len(models) == 0:
            print_info("No router models found - creating one to test")
            # Create a router model to test
            model_data = {
                "brand": "Test Brand",
                "model": "Test Model",
                "protocols": ["TR-069"],
                "isps": ["Test ISP"],
                "is_active": True
            }
            create_response = session.post(f"{BASE_URL}/router-models", json=model_data)
            if create_response.status_code == 200:
                models = [create_response.json()]
                print_success("Created test router model")
            else:
                print_error(f"Failed to create router model: {create_response.status_code}")
                return None
        
        # Check ID formats
        uuid_count = 0
        objectid_count = 0
        
        for model in models:
            model_id = model.get("id")
            if is_uuid(model_id):
                uuid_count += 1
            elif is_objectid(model_id):
                objectid_count += 1
                print_info(f"Found legacy ObjectId record: {model_id}")
        
        print_info(f"UUID records: {uuid_count}, ObjectId records: {objectid_count}")
        
        if len(models) > 0:
            print_success(f"✓ Successfully retrieved {len(models)} router models")
            return models[0].get("id")  # Return first model ID for further testing
        else:
            print_error("No router models available for testing")
            return None
    else:
        print_error(f"Failed to get router models: {response.status_code} - {response.text}")
        return None

def test_put_delete_operations(uuid_operator_id, model_id):
    """Test PUT/DELETE operations on both UUID and ObjectId records"""
    
    # Test PUT on UUID record (operator)
    if uuid_operator_id:
        print_test("UUID Migration - PUT Operation on UUID Record")
        
        update_data = {
            "contact_phone": "+9876543210"
        }
        
        response = session.put(f"{BASE_URL}/operators/{uuid_operator_id}", json=update_data)
        
        if response.status_code == 200:
            updated = response.json()
            if updated.get("contact_phone") == "+9876543210":
                print_success(f"✓ PUT operation successful on UUID record")
            else:
                print_error(f"✗ PUT operation failed - data not updated")
        else:
            print_error(f"PUT failed: {response.status_code} - {response.text}")
    
    # Test PUT on router model (could be UUID or ObjectId)
    if model_id:
        print_test("UUID Migration - PUT Operation on Router Model")
        
        update_data = {
            "notes": "Updated via test"
        }
        
        response = session.put(f"{BASE_URL}/router-models/{model_id}", json=update_data)
        
        if response.status_code == 200:
            updated = response.json()
            id_type = "UUID" if is_uuid(model_id) else "ObjectId" if is_objectid(model_id) else "Unknown"
            print_success(f"✓ PUT operation successful on {id_type} record")
        else:
            print_error(f"PUT failed: {response.status_code} - {response.text}")
    
    # Test DELETE on UUID record (operator)
    if uuid_operator_id:
        print_test("UUID Migration - DELETE Operation on UUID Record")
        
        response = session.delete(f"{BASE_URL}/operators/{uuid_operator_id}")
        
        if response.status_code == 200:
            print_success(f"✓ DELETE operation successful on UUID record")
        else:
            print_error(f"DELETE failed: {response.status_code} - {response.text}")

def test_realtime_polling_endpoint():
    """Test real-time device status polling endpoint"""
    print_test("Real-time Polling - GET /api/devices/status-updates")
    
    response = session.get(f"{BASE_URL}/devices/status-updates")
    
    if response.status_code == 200:
        print_success(f"✓ Endpoint returned 200 OK")
        
        try:
            data = response.json()
            
            if isinstance(data, list):
                print_success(f"✓ Response is a JSON array")
                print_info(f"  Found {len(data)} devices")
                
                if len(data) > 0:
                    # Check first device has required fields
                    device = data[0]
                    required_fields = ["id", "status", "last_seen", "ip_address"]
                    
                    missing_fields = []
                    for field in required_fields:
                        if field not in device:
                            missing_fields.append(field)
                    
                    if not missing_fields:
                        print_success(f"✓ All required fields present: {required_fields}")
                        print_info(f"  Sample device: {json.dumps(device, indent=2)}")
                    else:
                        print_error(f"✗ Missing fields: {missing_fields}")
                        print_info(f"  Device data: {json.dumps(device, indent=2)}")
                else:
                    print_info("  No devices in system (empty array is valid)")
                    print_success(f"✓ Endpoint structure is correct")
            else:
                print_error(f"✗ Response is not a JSON array: {type(data)}")
        except json.JSONDecodeError as e:
            print_error(f"✗ Invalid JSON response: {e}")
    else:
        print_error(f"Endpoint failed: {response.status_code} - {response.text}")

def main():
    print("\n" + "="*60)
    print("ACS Server Backend API Testing")
    print("Testing UUID Migration and Real-time Polling")
    print("="*60)
    
    # Login first
    if not login():
        print_error("Authentication failed - cannot proceed with tests")
        sys.exit(1)
    
    # Test UUID Migration
    print("\n" + "="*60)
    print("UUID MIGRATION TESTS")
    print("="*60)
    
    uuid_operator_id = test_uuid_migration()
    model_id = test_legacy_objectid_compatibility()
    test_put_delete_operations(uuid_operator_id, model_id)
    
    # Test Real-time Polling
    print("\n" + "="*60)
    print("REAL-TIME POLLING TESTS")
    print("="*60)
    
    test_realtime_polling_endpoint()
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
