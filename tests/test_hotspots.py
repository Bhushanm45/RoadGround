"""
Unit Tests for Hotspot Aggregation & Priority Scoring
=====================================================
Validates Haversine distance, clustering radius, independent ride deduplication,
and priority score formula.
"""

import os
import tempfile
import pytest

from backend.database import init_db, insert_raw_detection, get_all_hotspots
from backend.hotspots import (
    haversine_distance_meters,
    calculate_priority_score,
    process_and_aggregate_detection,
    CLUSTER_RADIUS_METERS
)


def test_haversine_distance():
    # Known distance test: Two points 0.0001 deg apart in latitude (~11.1 meters)
    lat1, lon1 = 18.5204, 73.8567
    lat2, lon2 = 18.5205, 73.8567
    dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
    assert 10.0 <= dist <= 12.0

    # Same point distance is zero
    assert haversine_distance_meters(lat1, lon1, lat1, lon1) == 0.0


def test_priority_score_calculation():
    # 1. Single low-severity pass should yield LOW or MEDIUM
    score_low, level_low = calculate_priority_score(
        distinct_rides=1,
        avg_confidence=0.70,
        max_severity=1.5,
        last_detected_iso="2026-10-19T20:00:00"
    )
    assert score_low < 60
    assert level_low in ["LOW", "MEDIUM"]

    # 2. Multi-ride confirmed severe pothole should yield HIGH
    score_high, level_high = calculate_priority_score(
        distinct_rides=4,
        avg_confidence=0.95,
        max_severity=3.8,
        last_detected_iso="2026-10-19T20:00:00"
    )
    assert score_high >= 70
    assert level_high == "HIGH"


def test_hotspot_spatial_clustering_and_deduplication():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = os.path.join(tmp_dir, "test_clustering.db")
        init_db(test_db)

        # Detection 1: Bus 01 hits pothole on FC Road
        det1 = {
            "class": "POTHOLE",
            "confidence": 0.92,
            "severity_metric": 3.2,
            "ride_id": "RIDE_01",
            "gps": {"latitude": 18.52040, "longitude": 73.85670, "valid": True}
        }
        id1 = insert_raw_detection(det1, db_path=test_db)
        h_id1 = process_and_aggregate_detection(det1, id1, db_path=test_db)
        assert h_id1 is not None

        # Detection 2: SAME RIDE (e.g. rear axle hitting the same pothole 1.5 seconds later)
        # Offset by 3 meters
        det2 = {
            "class": "POTHOLE",
            "confidence": 0.90,
            "severity_metric": 2.9,
            "ride_id": "RIDE_01",
            "gps": {"latitude": 18.52042, "longitude": 73.85671, "valid": True}
        }
        id2 = insert_raw_detection(det2, db_path=test_db)
        h_id2 = process_and_aggregate_detection(det2, id2, db_path=test_db)

        # Must cluster into the EXACT same hotspot
        assert h_id2 == h_id1

        hotspots = get_all_hotspots(db_path=test_db)
        assert len(hotspots) == 1
        # Total observation count is 2, but distinct rides remains 1!
        assert hotspots[0]["observation_count"] == 2
        assert hotspots[0]["distinct_rides"] == 1

        # Detection 3: INDEPENDENT RIDE (Bus 02 on the next morning pass)
        det3 = {
            "class": "POTHOLE",
            "confidence": 0.94,
            "severity_metric": 3.4,
            "ride_id": "RIDE_02",
            "gps": {"latitude": 18.52041, "longitude": 73.85672, "valid": True}
        }
        id3 = insert_raw_detection(det3, db_path=test_db)
        h_id3 = process_and_aggregate_detection(det3, id3, db_path=test_db)

        assert h_id3 == h_id1
        hotspots = get_all_hotspots(db_path=test_db)
        # Distinct rides must now increment to 2!
        assert hotspots[0]["observation_count"] == 3
        assert hotspots[0]["distinct_rides"] == 2


def test_missing_or_invalid_gps_is_not_clustered():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_db = os.path.join(tmp_dir, "test_nogps.db")
        init_db(test_db)

        det_nogps = {
            "class": "POTHOLE",
            "confidence": 0.90,
            "severity_metric": 2.5,
            "ride_id": "RIDE_01",
            "gps": {"latitude": None, "longitude": None, "valid": False}
        }
        id1 = insert_raw_detection(det_nogps, db_path=test_db)
        h_id = process_and_aggregate_detection(det_nogps, id1, db_path=test_db)

        # Cannot form a geographic hotspot without GPS
        assert h_id is None
        assert len(get_all_hotspots(db_path=test_db)) == 0
