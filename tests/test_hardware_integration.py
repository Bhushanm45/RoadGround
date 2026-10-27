"""
Hardware Integration and GPS Telemetry Tests
============================================
Validates hardware telemetry ingestion, strict GPS coordinate validation,
Null Island rejection, stale fix detection, device heartbeats, and mode segregation.
"""

import time
import pytest
from backend.app import app
from backend.database import init_db, get_registered_devices, DEFAULT_DB_PATH
from backend.hotspots import validate_gps_coordinates
from ml.simulate_sensors import generate_single_window_samples


@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as client:
        yield client


def test_gps_coordinate_validation():
    # Valid Pune coordinate
    assert validate_gps_coordinates(18.5204, 73.8567, fix_valid=True, is_stale=False) is True

    # Null Island (0.0, 0.0) rejection
    assert validate_gps_coordinates(0.0, 0.0, fix_valid=True, is_stale=False) is False
    assert validate_gps_coordinates(0.00001, -0.00001, fix_valid=True, is_stale=False) is False

    # Out of range coordinates
    assert validate_gps_coordinates(95.0, 73.8567, fix_valid=True) is False
    assert validate_gps_coordinates(18.5204, 190.0, fix_valid=True) is False

    # Stale GPS fix rejection
    assert validate_gps_coordinates(18.5204, 73.8567, fix_valid=True, is_stale=True) is False

    # Invalid fix flag
    assert validate_gps_coordinates(18.5204, 73.8567, fix_valid=False, is_stale=False) is False


def test_hardware_telemetry_ingest_and_heartbeat(client):
    ax, ay, az, gx, gy, gz = generate_single_window_samples("NORMAL_ROAD", n_samples=100)
    samples = []
    for i in range(100):
        samples.append({
            "t": int(time.time() * 1000) + (i * 10),
            "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]),
            "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])
        })

    payload = {
        "device_id": "ESP32_TEST_UNIT",
        "mode": "HARDWARE",
        "seq_num": 1,
        "firmware_version": "1.2.0",
        "gps": {
            "latitude": 18.5204,
            "longitude": 73.8567,
            "speed_kmh": 32.0,
            "fix_valid": True,
            "satellites": 8,
            "hdop": 1.1,
            "timestamp_ms": int(time.time() * 1000)
        },
        "samples": samples
    }

    res = client.post("/api/telemetry", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["mode"] == "HARDWARE"

    # Query device status
    dev_res = client.get("/api/device-status")
    assert dev_res.status_code == 200
    dev_data = dev_res.get_json()
    assert dev_data["count"] >= 1
    target = next((d for d in dev_data["devices"] if d["device_id"] == "ESP32_TEST_UNIT"), None)
    assert target is not None
    assert target["status"] == "ONLINE"
    assert target["satellites"] == 8
    assert target["last_seq_num"] == 1


def test_null_island_rejection_in_telemetry(client):
    # Detection with 0,0 GPS coordinates must not create a mapped hotspot
    ax, ay, az, gx, gy, gz = generate_single_window_samples("POTHOLE", n_samples=100)
    samples = []
    for i in range(100):
        samples.append({
            "t": int(time.time() * 1000) + (i * 10),
            "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]),
            "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])
        })

    payload = {
        "device_id": "ESP32_NULL_ISLAND",
        "mode": "HARDWARE",
        "seq_num": 2,
        "gps": {
            "latitude": 0.0,
            "longitude": 0.0,
            "fix_valid": True
        },
        "samples": samples
    }

    res = client.post("/api/telemetry", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["latest_prediction"] is not None
    # Must be unlocated
    assert data["latest_prediction"]["location_status"] == "UNLOCATED_NO_GPS"
    assert data["latest_prediction"]["hotspot_id"] is None


def test_mode_segregation_in_hotspots(client):
    # Seed simulation demo data
    client.post("/api/demo/seed")

    # Ingest a real HARDWARE pothole at a distinct coordinate
    ax, ay, az, gx, gy, gz = generate_single_window_samples("POTHOLE", n_samples=100)
    samples = []
    for i in range(100):
        samples.append({
            "t": int(time.time() * 1000) + (i * 10),
            "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]),
            "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])
        })

    payload = {
        "device_id": "ESP32_REAL_HW",
        "mode": "HARDWARE",
        "seq_num": 10,
        "gps": {
            "latitude": 18.5350,
            "longitude": 73.8400,
            "fix_valid": True,
            "timestamp_ms": int(time.time() * 1000)
        },
        "samples": samples
    }
    client.post("/api/telemetry", json=payload)

    # Query with mode=HARDWARE
    hw_res = client.get("/api/hotspots?mode=HARDWARE")
    assert hw_res.status_code == 200
    hw_data = hw_res.get_json()
    for h in hw_data["hotspots"]:
        assert h["mode"] == "HARDWARE"

    # Query with mode=SIMULATION
    sim_res = client.get("/api/hotspots?mode=SIMULATION")
    assert sim_res.status_code == 200
    sim_data = sim_res.get_json()
    for h in sim_data["hotspots"]:
        assert h["mode"] == "SIMULATION"


def test_model_status_endpoint(client):
    res = client.get("/api/model-status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["readiness"] in ["MODEL_READY", "MODEL_NOT_READY"]
    if data["readiness"] == "MODEL_READY":
        assert "POTHOLE" in data["classes"]
        assert data["features_count"] == 23


def test_hardware_position_endpoint_valid_fix(client):
    """Verifies that /api/hardware-position returns real GPS coordinates when fix is valid."""
    ax, ay, az, gx, gy, gz = generate_single_window_samples("NORMAL_ROAD", n_samples=100)
    samples = [{"t": int(time.time() * 1000) + (i * 10), "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]), "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])} for i in range(100)]

    payload = {
        "device_id": "ESP32_VEHICLE_GPS",
        "mode": "HARDWARE",
        "seq_num": 101,
        "gps": {
            "latitude": 18.520432,
            "longitude": 73.856740,
            "speed_kmh": 28.5,
            "fix_valid": True,
            "satellites": 9,
            "hdop": 1.05,
            "timestamp_ms": int(time.time() * 1000)
        },
        "samples": samples
    }
    post_res = client.post("/api/telemetry", json=payload)
    assert post_res.status_code == 200

    # Query hardware position
    pos_res = client.get("/api/hardware-position?mode=HARDWARE")
    assert pos_res.status_code == 200
    pos_data = pos_res.get_json()
    assert pos_data["connected"] is True
    assert pos_data["device_id"] == "ESP32_VEHICLE_GPS"
    assert pos_data["gps_fix"] is True
    assert pos_data["fix_status"] == "3D_FIX"
    assert pos_data["satellites"] == 9
    assert pos_data["position"] is not None
    assert pytest.approx(pos_data["position"]["latitude"], 0.0001) == 18.520432
    assert pytest.approx(pos_data["position"]["longitude"], 0.0001) == 73.856740
    assert pos_data["is_stale"] is False


def test_hardware_position_searching_no_false_coordinates(client):
    """Verifies that when GPS is searching (no fix), no false (0,0) coordinates are published."""
    ax, ay, az, gx, gy, gz = generate_single_window_samples("NORMAL_ROAD", n_samples=100)
    samples = [{"t": int(time.time() * 1000) + (i * 10), "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]), "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])} for i in range(100)]

    payload = {
        "device_id": "ESP32_SEARCHING_UNIT",
        "mode": "HARDWARE",
        "seq_num": 1,
        "gps": {
            "latitude": None,
            "longitude": None,
            "fix_valid": False,
            "satellites": 2,
            "hdop": 99.0
        },
        "samples": samples
    }
    client.post("/api/telemetry", json=payload)

    dev_res = client.get("/api/device-status")
    assert dev_res.status_code == 200
    target = next((d for d in dev_res.get_json()["devices"] if d["device_id"] == "ESP32_SEARCHING_UNIT"), None)
    assert target is not None
    assert target["gps_fix"] == 0
    assert target["latitude"] is None
    assert target["longitude"] is None


def test_stale_gps_telemetry_rejection(client):
    """Verifies that GPS timestamps older than 10 seconds are marked as stale."""
    ax, ay, az, gx, gy, gz = generate_single_window_samples("POTHOLE", n_samples=100)
    samples = [{"t": int(time.time() * 1000) + (i * 10), "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]), "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])} for i in range(100)]

    # Old GPS fix timestamp from 25 seconds ago
    stale_timestamp_ms = int((time.time() - 25.0) * 1000)
    payload = {
        "device_id": "ESP32_STALE_UNIT",
        "mode": "HARDWARE",
        "seq_num": 5,
        "gps": {
            "latitude": 18.5204,
            "longitude": 73.8567,
            "fix_valid": True,
            "timestamp_ms": stale_timestamp_ms
        },
        "samples": samples
    }
    res = client.post("/api/telemetry", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    # Must reject stale GPS from clustering
    if data["latest_prediction"] and data["latest_prediction"].get("is_hazard"):
        assert data["latest_prediction"]["location_status"] == "UNLOCATED_NO_GPS"
        assert data["latest_prediction"]["hotspot_id"] is None


def test_network_info_endpoint(client):
    """Verifies that /api/network-info returns the host LAN IP and instructions."""
    res = client.get("/api/network-info")
    assert res.status_code == 200
    data = res.get_json()
    assert "laptop_lan_ip" in data
    assert "port" in data
    assert "backend_url" in data
    assert "api/telemetry" in data["backend_url"]
    assert "secrets.h" in data["instructions"]


def test_microcontroller_uptime_telemetry_freshness(client):
    """
    CRITICAL FIX VERIFICATION:
    Verifies that ESP32 telemetry sending uptime millis (e.g. millis() = 15000)
    is NOT falsely rejected as 56-year-old stale Unix epoch data!
    """
    ax, ay, az, gx, gy, gz = generate_single_window_samples("NORMAL_ROAD", n_samples=100)
    samples = [{"t": 15000 + (i * 10), "ax": float(ax[i]), "ay": float(ay[i]), "az": float(az[i]), "gx": float(gx[i]), "gy": float(gy[i]), "gz": float(gz[i])} for i in range(100)]

    payload = {
        "device_id": "ESP32_UPTIME_FRESH",
        "mode": "HARDWARE",
        "seq_num": 1,
        "firmware_version": "1.3.1",
        "gps": {
            "latitude": 18.520432,
            "longitude": 73.856740,
            "speed_kmh": 22.0,
            "fix_valid": True,
            "satellites": 7,
            "hdop": 1.2,
            "timestamp_ms": 15000  # Microcontroller uptime: 15s since boot
        },
        "samples": samples
    }
    res = client.post("/api/telemetry", json=payload)
    assert res.status_code == 200

    dev_res = client.get("/api/device-status")
    assert dev_res.status_code == 200
    target = next((d for d in dev_res.get_json()["devices"] if d["device_id"] == "ESP32_UPTIME_FRESH"), None)
    assert target is not None
    assert target["status"] == "ONLINE"
    assert target["gps_fix"] == 1
    assert target["latitude"] is not None
    assert target["is_stale"] == 0


def test_telemetry_malformed_and_missing_fields_rejection(client):
    """Verifies that invalid or empty payloads are rejected with 400 Bad Request."""
    # Completely empty body
    res1 = client.post("/api/telemetry", json={})
    assert res1.status_code == 400

    # Missing samples array
    res2 = client.post("/api/telemetry", json={"device_id": "ESP32_BAD", "samples": "not_a_list"})
    assert res2.status_code == 400


