"""Backend API tests for ACS Server"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

ADMIN_EMAIL = "admin@acsserver.com"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def auth_session(session):
    resp = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    return session


# Health
class TestHealth:
    def test_health(self, session):
        r = session.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        print("Health check passed")


# Auth
class TestAuth:
    def test_login_success(self, session):
        r = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200
        data = r.json()
        assert data.get("email") == ADMIN_EMAIL or data.get("user", {}).get("email") == ADMIN_EMAIL
        role = data.get("role") or data.get("user", {}).get("role")
        assert role == "super_admin"
        print("Login success")

    def test_login_wrong_password(self, session):
        r = session.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": "WrongPass"})
        assert r.status_code in [401, 400]
        print("Login failure handled correctly")

    def test_me(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        print("Me endpoint works")


# Stats
class TestStats:
    def test_get_stats(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/stats")
        assert r.status_code == 200
        data = r.json()
        for key in ["total_devices", "online_devices", "offline_devices", "unknown_devices"]:
            assert key in data, f"Missing key: {key}"
        print(f"Stats: {data}")


# Devices
class TestDevices:
    device_id = None
    op_id = None

    def test_get_devices(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/devices")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"Devices count: {len(r.json())}")

    def test_create_device(self, auth_session):
        # First create an operator
        op_resp = auth_session.post(f"{BASE_URL}/api/operators", json={
            "name": "TEST_Op_ForDevice",
            "code": "TEST_OP_DEV",
            "contact_email": "testopdev@test.com",
        })
        op_id = op_resp.json().get("id") if op_resp.status_code in [200, 201] else None

        payload = {
            "name": "TEST_Device_001",
            "serial_number": "TEST-SN-99999",
            "ip_address": "192.168.1.100",
            "model": "Huawei HG8245H",
            "protocol": "TR-069",
            "operator_id": op_id or "000000000000000000000000",
        }
        r = auth_session.post(f"{BASE_URL}/api/devices", json=payload)
        assert r.status_code in [200, 201], f"Create failed: {r.text}"
        data = r.json()
        assert "id" in data or "_id" in data
        TestDevices.device_id = data.get("id") or data.get("_id")
        TestDevices.op_id = op_id
        print(f"Created device id: {TestDevices.device_id}")

    def test_get_device_by_id(self, auth_session):
        if not TestDevices.device_id:
            pytest.skip("No device created")
        r = auth_session.get(f"{BASE_URL}/api/devices/{TestDevices.device_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_Device_001"
        print("Get device by id works")

    def test_delete_device(self, auth_session):
        if not TestDevices.device_id:
            pytest.skip("No device created")
        r = auth_session.delete(f"{BASE_URL}/api/devices/{TestDevices.device_id}")
        assert r.status_code in [200, 204]
        print("Delete device works")


# Router Models
class TestRouterModels:
    def test_get_router_models(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/router-models")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 18, f"Expected >=18 models, got {len(data)}"
        print(f"Router models count: {len(data)}")


# ACS Status
class TestACS:
    def test_acs_status(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/acs/status")
        assert r.status_code == 200
        print(f"ACS status: {r.json()}")


# Settings
class TestSettings:
    def test_get_settings(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/settings")
        assert r.status_code == 200
        data = r.json()
        assert "ai_enabled" in data
        print("Settings endpoint works")


# Operators
class TestOperators:
    op_id = None

    def test_get_operators(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/operators")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        print(f"Operators count: {len(r.json())}")

    def test_create_operator(self, auth_session):
        payload = {
            "name": "TEST_Operator_One",
            "code": "TEST_OP_001",
            "contact_email": "testop001@test.com",
            "contact_phone": "9876543210",
        }
        r = auth_session.post(f"{BASE_URL}/api/operators", json=payload)
        assert r.status_code in [200, 201], f"Create operator failed: {r.text}"
        data = r.json()
        TestOperators.op_id = data.get("id") or data.get("_id")
        print(f"Created operator id: {TestOperators.op_id}")

    def test_delete_operator(self, auth_session):
        if not TestOperators.op_id:
            pytest.skip("No operator created")
        r = auth_session.delete(f"{BASE_URL}/api/operators/{TestOperators.op_id}")
        assert r.status_code in [200, 204]
        print("Delete operator works")
