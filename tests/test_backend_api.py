"""
Integration Tests for Flask Backend API and Database Layer
===========================================================
Validates REST endpoints, telemetry batch ingestion, live inference,
SQLite audit tracking, and dashboard endpoints.
"""

import os
import json
import pytest
from backend.app import app
from backend.database import init_db, DEFAULT_DB_PATH
from ml.simulate_sensors import generate_single_window_samples


@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as client:
        yield client


def test_system_status_endpoint(client):
    res = client.get("/api/system-status")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "online"
    assert "model_loaded" in data


def test_seed_demo_hotspots(client):
    res = client.post("/api/demo/seed")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "seeded"

    # Query hotspots
    h_res = client.get("/api/hotspots")
    assert h_res.status_code == 200
    h_data = h_res.get_json()
    assert h_data["count"] >= 5


def test_stats_endpoint(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "open_reports" in data
    assert "high_priority" in data
    assert "resolved" in data


def test_telemetry_batch_ingest_and_inference(client):
    # Generate 100 samples of a pothole
    ax, ay, az, gx, gy, gz = generate_single_window_samples("POTHOLE", n_samples=100)
    samples = []
    for i in range(100):
        samples.append({
            "t": 1697720000000 + (i * 10),
            "ax": float(ax[i]),
            "ay": float(ay[i]),
            "az": float(az[i]),
            "gx": float(gx[i]),
            "gy": float(gy[i]),
            "gz": float(gz[i])
        })

    payload = {
        "device_id": "TEST_ESP32_01",
        "ride_id": "TEST_RIDE_999",
        "gps": {
            "latitude": 18.5204,
            "longitude": 73.8567,
            "speed_kmh": 28.5,
            "fix_valid": True
        },
        "samples": samples
    }

    res = client.post("/api/telemetry", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["received_samples"] == 100
    assert data["latest_prediction"] is not None
    assert data["latest_prediction"]["class"] == "POTHOLE"
    assert data["alert"] is True


def test_telemetry_malformed_payload(client):
    res = client.post("/api/telemetry", json={"bad_key": 123})
    assert res.status_code == 400


def test_workflow_status_transition(client):
    # Seed demo data first
    client.post("/api/demo/seed")
    h_res = client.get("/api/hotspots")
    hotspot_id = h_res.get_json()["hotspots"][0]["id"]

    # Valid update
    update_res = client.post(
        f"/api/hotspots/{hotspot_id}/status",
        json={"status": "INSPECTION_REQUESTED", "notes": "Inspector dispatched"}
    )
    assert update_res.status_code == 200

    # Invalid status
    bad_res = client.post(
        f"/api/hotspots/{hotspot_id}/status",
        json={"status": "INVALID_STATE"}
    )
    assert bad_res.status_code == 400

    # Non-existent hotspot
    missing_res = client.post(
        "/api/hotspots/99999/status",
        json={"status": "VERIFIED"}
    )
    assert missing_res.status_code == 404


def test_dashboard_page_load(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"RoadGuard AI" in res.data
    assert b"Pune Municipal Corporation" in res.data
