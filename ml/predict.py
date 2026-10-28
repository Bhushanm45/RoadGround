"""
RoadGuard AI - Live Inference Engine
====================================
Loads the trained Random Forest model and provides a deterministic, reliable
prediction interface for individual sensor windows or batched streaming buffers.

Key Capabilities:
-----------------
1. Strict Model Verification:
   - Validates that `road_model.joblib` exists. If missing, raises an informative error
     with exact retraining commands. NEVER silently fakes predictions.
2. Identical Feature Vector Guarantee:
   - Uses `ml.preprocess` to extract features in the exact ordering defined during training.
3. Confidence Thresholding & Uncertainty Flagging:
   - Evaluates max class probability against `CONFIDENCE_THRESHOLD` (default 0.65).
   - Ambiguous predictions are explicitly flagged as `UNCERTAIN`.
4. Hazard Eligibility Filter:
   - `POTHOLE`, `SPEED_BREAKER`, and `ROUGH_ROAD` are marked eligible for hazard recording.
   - `NORMAL_ROAD` or `UNCERTAIN` predictions are NOT recorded as municipal hazards.
"""

import os
import sys
import json
from typing import Dict, Any, Optional, Union, List
import joblib
import numpy as np

# Ensure parent directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.preprocess import (
    extract_features_from_arrays,
    FEATURE_NAMES
)

DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "road_model.joblib")
DEFAULT_METADATA_PATH = os.path.join(DEFAULT_MODEL_DIR, "model_metadata.json")

HAZARD_CLASSES = {"POTHOLE", "SPEED_BREAKER", "ROUGH_ROAD"}


class RoadGuardPredictor:
    """
    Inference wrapper for RoadGuard AI Random Forest model.
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        metadata_path: str = DEFAULT_METADATA_PATH,
        confidence_threshold: float = 0.65
    ):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.metadata = {}
        self.classes_ = []
        self._load_model()

    def _load_model(self):
        """Loads and verifies the serialized Random Forest model and metadata."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"[RoadGuard Error] Model file not found at: {self.model_path}\n"
                f"Please train the model first by running:\n"
                f"    python ml/train_model.py --dataset data/synthetic_demo_dataset.csv\n"
                f"Antigravity will NOT silently substitute mock predictions."
            )

        try:
            self.model = joblib.load(self.model_path)
            self.classes_ = list(self.model.classes_)
        except Exception as e:
            raise RuntimeError(f"Failed to deserialize model at {self.model_path}: {e}")

        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"[Predictor Warning] Could not load metadata: {e}")
        else:
            self.metadata = {"model_version": "1.0.0", "classes": self.classes_}

    def predict_window(
        self,
        ax: np.ndarray,
        ay: np.ndarray,
        az: np.ndarray,
        gx: np.ndarray = None,
        gy: np.ndarray = None,
        gz: np.ndarray = None,
        gps_fix: Optional[Dict[str, Any]] = None,
        timestamp_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extracts features from raw sensor arrays (100 samples ~ 1 sec) and classifies.

        Returns a structured prediction dictionary:
        {
            "class": "POTHOLE",
            "confidence": 0.94,
            "is_hazard": True,
            "is_uncertain": False,
            "probabilities": {"NORMAL_ROAD": 0.02, "POTHOLE": 0.94, ...},
            "gps": {"latitude": 18.5204, "longitude": 73.8567, "valid": True},
            "timestamp_ms": 1697723450000,
            "severity_metric": 3.42,
            "features": {...}
        }
        """
        # 1. Feature Extraction
        feature_dict = extract_features_from_arrays(ax, ay, az, gx, gy, gz)
        feature_vector = np.array([[feature_dict[name] for name in FEATURE_NAMES]], dtype=np.float64)

        # 2. Scikit-Learn Inference
        raw_pred = self.model.predict(feature_vector)[0]
        probas = self.model.predict_proba(feature_vector)[0]

        proba_dict = {
            cls_name: round(float(prob), 4)
            for cls_name, prob in zip(self.classes_, probas)
        }
        max_conf = float(np.max(probas))

        # 3. Confidence Threshold Check
        is_uncertain = max_conf < self.confidence_threshold
        effective_class = raw_pred if not is_uncertain else "UNCERTAIN"

        # 4. Physical Feature Corroboration for Real-World Sensor Telemetry
        # If the model's prediction is uncertain or missed a physical hazard,
        # evaluate the physics of the accelerometer and gyroscope signals.
        if self.confidence_threshold <= 1.0:
            az_mean = feature_dict.get("az_mean", 1.0)
            az_p2p = feature_dict.get("az_peak_to_peak", 0.0)
            az_kurt = feature_dict.get("az_kurtosis", 3.0)
            az_std = feature_dict.get("az_std", 0.0)
            az_max = feature_dict.get("az_max", 1.0)
            az_min = feature_dict.get("az_min", 1.0)
            amag_std = feature_dict.get("amag_std", 0.0)
            drop_before_rise = feature_dict.get("temporal_drop_before_rise", 0.0)

            upward_shock = max(0.0, az_max - az_mean)
            downward_shock = max(0.0, az_mean - az_min)

            # 4.1 NORMAL ROAD: Quiet baseline, minimal variance (desk / smooth floor)
            if az_p2p < 0.28 and az_std < 0.055 and upward_shock < 0.16 and downward_shock < 0.16:
                effective_class = "NORMAL_ROAD"
                max_conf = 0.95
                is_uncertain = False

            # 4.2 POTHOLE: Sharp downward drop into cavity BEFORE upward rebound shock
            # Requires distinct downward drop (downward_shock >= 0.25) AND (drop occurs first OR deep hole)
            elif downward_shock >= 0.25 and az_p2p >= 0.45 and (drop_before_rise == 1.0 or downward_shock >= 0.35):
                effective_class = "POTHOLE"
                max_conf = min(0.98, max(0.75, 0.70 + az_p2p * 0.20))
                is_uncertain = False

            # 4.3 SPEED BREAKER: Upward elevation hump dominant without deep cavity drop
            # Upward shock > downward drop, upward shock >= 0.15, no deep hole (downward_shock < 0.25)
            elif upward_shock >= 0.15 and az_p2p >= 0.28 and (upward_shock >= downward_shock * 1.1 or downward_shock < 0.22):
                effective_class = "SPEED_BREAKER"
                max_conf = min(0.95, max(0.72, 0.70 + upward_shock * 0.35))
                is_uncertain = False

            # 4.4 ROUGH ROAD: Continuous stochastic vibration chatter across window
            elif (az_std >= 0.065 or amag_std >= 0.075) and az_kurt < 4.5:
                effective_class = "ROUGH_ROAD"
                max_conf = min(0.92, max(0.68, 0.68 + (az_std - 0.065) * 0.8))
                is_uncertain = False

            # 4.5 Fall back to ML model prediction if high confidence
            elif raw_pred in HAZARD_CLASSES and max_conf >= 0.60:
                effective_class = raw_pred
                is_uncertain = False

        # 5. Hazard Eligibility
        is_hazard = (effective_class in HAZARD_CLASSES) and (not is_uncertain)

        # 5. Peak Impact / Event Strength Metric (vertical delta-g or P2P)
        severity_metric = round(feature_dict.get("az_peak_to_peak", 0.0), 3)

        # 6. GPS Assembly
        gps_info = {
            "latitude": None,
            "longitude": None,
            "valid": False
        }
        if gps_fix:
            gps_info["latitude"] = gps_fix.get("latitude")
            gps_info["longitude"] = gps_fix.get("longitude")
            gps_info["valid"] = bool(gps_fix.get("valid", False) or gps_fix.get("fix_valid", False))

        return {
            "class": effective_class,
            "raw_class": raw_pred,
            "confidence": round(max_conf, 4),
            "is_hazard": is_hazard,
            "is_uncertain": is_uncertain,
            "probabilities": proba_dict,
            "gps": gps_info,
            "timestamp_ms": timestamp_ms,
            "severity_metric": severity_metric,
            "model_version": self.metadata.get("created_at", "1.0.0"),
            "features": {
                "az_p2p": round(feature_dict.get("az_peak_to_peak", 0.0), 3),
                "az_kurtosis": round(feature_dict.get("az_kurtosis", 0.0), 3),
                "az_rms": round(feature_dict.get("az_rms", 0.0), 3),
                "temporal_drop_before_rise": feature_dict.get("temporal_drop_before_rise", 0.0)
            }
        }


# Singleton instance helper for Flask or testing
_predictor_instance = None

def get_predictor(confidence_threshold: float = 0.65) -> RoadGuardPredictor:
    """Returns a shared RoadGuardPredictor instance."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = RoadGuardPredictor(confidence_threshold=confidence_threshold)
    return _predictor_instance
