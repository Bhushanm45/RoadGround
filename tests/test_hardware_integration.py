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
