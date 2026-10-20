"""
Unit Tests for Machine Learning Training, Persistence, and Prediction
=====================================================================
Validates Random Forest training pipeline, joblib serialization,
prediction schema, and confidence thresholding.
"""

import os
import tempfile
import pytest
import numpy as np

from ml.predict import RoadGuardPredictor, HAZARD_CLASSES
from ml.simulate_sensors import generate_single_window_samples, generate_synthetic_dataset
from ml.train_model import train_and_evaluate


def test_predict_window_pothole_vs_normal():
    # Use existing trained model
    predictor = RoadGuardPredictor(confidence_threshold=0.60)

    # 1. Pothole sample
    ax_p, ay_p, az_p, gx_p, gy_p, gz_p = generate_single_window_samples("POTHOLE", n_samples=100, seed=42)
    pred_p = predictor.predict_window(
        ax_p, ay_p, az_p, gx_p, gy_p, gz_p,
        gps_fix={"latitude": 18.5204, "longitude": 73.8567, "fix_valid": True},
        timestamp_ms=1697720000000
    )

    assert pred_p["class"] == "POTHOLE"
    assert pred_p["is_hazard"] is True
    assert pred_p["confidence"] >= 0.60
    assert pred_p["gps"]["latitude"] == 18.5204
    assert "az_kurtosis" in pred_p["features"]

    # 2. Normal road sample
    ax_n, ay_n, az_n, gx_n, gy_n, gz_n = generate_single_window_samples("NORMAL_ROAD", n_samples=100, seed=42)
    pred_n = predictor.predict_window(ax_n, ay_n, az_n, gx_n, gy_n, gz_n)

    assert pred_n["class"] == "NORMAL_ROAD"
    assert pred_n["is_hazard"] is False


def test_uncertainty_thresholding():
    # If confidence threshold is set strictly above 1.0 (e.g. 1.01), any prediction must flag UNCERTAIN
    predictor = RoadGuardPredictor(confidence_threshold=1.01)
    ax, ay, az, gx, gy, gz = generate_single_window_samples("ROUGH_ROAD", n_samples=100)

    pred = predictor.predict_window(ax, ay, az, gx, gy, gz)
    assert pred["is_uncertain"] is True
    assert pred["class"] == "UNCERTAIN"
    assert pred["is_hazard"] is False  # Uncertain events are not published as hazards


def test_missing_model_file_raises_informative_error():
    with pytest.raises(FileNotFoundError) as exc_info:
        RoadGuardPredictor(model_path="non_existent_model_dir/fake.joblib")
    assert "Model file not found" in str(exc_info.value)
    assert "python ml/train_model.py" in str(exc_info.value)


def test_mini_model_training_and_eval():
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = os.path.join(tmp_dir, "mini_dataset.csv")
        models_out = os.path.join(tmp_dir, "models")

        # Generate a small 4-ride dataset
        generate_synthetic_dataset(csv_path, n_rides=4, windows_per_ride=20, seed=123)

        model, metadata = train_and_evaluate(
            dataset_csv=csv_path,
            output_dir=models_out,
            n_estimators=25,
            test_size=0.25
        )

        assert os.path.exists(os.path.join(models_out, "road_model.joblib"))
        assert os.path.exists(os.path.join(models_out, "model_metadata.json"))
        assert metadata["metrics"]["accuracy"] >= 0.85
        assert len(metadata["classes"]) == 4
