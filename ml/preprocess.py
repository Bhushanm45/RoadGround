"""
RoadGuard AI - Preprocessing and Feature Extraction Pipeline
=============================================================
This module provides a unified, deterministic feature extraction pipeline
used identically during model training, offline validation, and live inference.

Scientific Rationale:
---------------------
Road surface anomalies produce distinct mechanical vibration signatures on a vehicle chassis:
1. Potholes (Cavity):
   - Cause a sharp sudden downward acceleration drop as the wheel drops into the void,
     followed immediately by a high-energy rebound shock spike when impacting the cavity edge.
   - Characterized by high vertical peak-to-peak amplitude (Δg), high kurtosis (impulsive peakedness),
     and negative drop occurring before the rebound crest.
2. Speed Breakers (Elevation):
   - Cause a smooth, low-frequency sinusoidal elevation pulse without high-frequency shock chatter.
   - Characterized by moderate peak-to-peak delta, low kurtosis (smooth bell curve), and longer duration.
3. Rough Road (Continuous Irregularity):
   - Causes continuous stochastic chatter around the 1.0g gravity baseline.
   - Characterized by elevated standard deviation and variance across all axes without a single isolated shock.
4. Normal Road:
   - Steady 1.0g baseline on Z with minimal variance (standard deviation < 0.08g).

Feature Mathematical Definitions:
---------------------------------
- Acceleration Magnitude: a_mag = sqrt(ax^2 + ay^2 + az^2)
- Mean: mu = (1/N) * sum(x_i)
- Standard Deviation: sigma = sqrt((1/N) * sum((x_i - mu)^2))
- RMS (Root Mean Square): sqrt((1/N) * sum(x_i^2))
- Peak-to-Peak (P2P): max(x) - min(x)
- Kurtosis: Pearson's kurtosis = [(1/N) * sum((x_i - mu)^4)] / [sigma^4]
- Crest Factor: max(|x_i|) / RMS
- Vibration Energy: (1/N) * sum((az - 1.0g)^2)
- Temporal Drop-Before-Rise: 1.0 if argmin(az) < argmax(az) else 0.0
"""

from typing import List, Dict, Any, Union
import numpy as np
import pandas as pd


# Canonical ordered list of features extracted per time window
FEATURE_NAMES: List[str] = [
    "az_mean",
    "az_std",
    "az_min",
    "az_max",
    "az_peak_to_peak",
    "az_rms",
    "az_kurtosis",
    "az_crest_factor",
    "az_energy",
    "amag_mean",
    "amag_std",
    "amag_min",
    "amag_max",
    "amag_peak_to_peak",
    "amag_rms",
    "amag_kurtosis",
    "ax_std",
    "ax_peak_to_peak",
    "ay_std",
    "ay_peak_to_peak",
    "temporal_drop_before_rise",
    "z_min_max_ratio",
    "gyro_magnitude_mean"
]

DEFAULT_SAMPLING_RATE_HZ = 100
DEFAULT_WINDOW_SECONDS = 1.0
DEFAULT_STEP_SECONDS = 0.5


def get_feature_names() -> List[str]:
    """Returns the ordered list of feature names."""
    return list(FEATURE_NAMES)


def calculate_kurtosis(values: np.ndarray) -> float:
    """
    Computes Pearson's kurtosis:
    kurtosis = [ (1/N) * sum((x - mu)^4) ] / [ std^4 ]
    Normal distribution has kurtosis ~ 3.0.
    A sharp impact shock (pothole rebound) produces high kurtosis (> 5.0).
    """
    n = len(values)
    if n < 4:
        return 3.0
    mean_val = float(np.mean(values))
    std_val = float(np.std(values))
    if std_val < 1e-6:
        return 3.0
    fourth_moment = float(np.mean((values - mean_val) ** 4))
    return float(fourth_moment / (std_val ** 4))


def extract_features_from_arrays(
    ax: np.ndarray,
    ay: np.ndarray,
    az: np.ndarray,
    gx: np.ndarray = None,
    gy: np.ndarray = None,
    gz: np.ndarray = None
) -> Dict[str, float]:
    """
    Extracts numerical features from raw sensor arrays corresponding to a single time window.

    Parameters:
        ax, ay, az: 1D numpy arrays of linear acceleration (in g)
        gx, gy, gz: (Optional) 1D numpy arrays of angular velocity (in deg/s)

    Returns:
        dict mapping feature name to numerical float value
    """
    # Sanitize and convert inputs
    ax = np.asarray(ax, dtype=np.float64)
    ay = np.asarray(ay, dtype=np.float64)
    az = np.asarray(az, dtype=np.float64)

    # Clean NaNs or Infinities
    ax = np.nan_to_num(ax, nan=0.0, posinf=0.0, neginf=0.0)
    ay = np.nan_to_num(ay, nan=0.0, posinf=0.0, neginf=0.0)
    az = np.nan_to_num(az, nan=1.0, posinf=1.0, neginf=1.0)

    n_samples = len(az)
    if n_samples == 0:
        raise ValueError("Cannot extract features from an empty sensor array.")

    # 1. Acceleration Magnitude: sqrt(ax^2 + ay^2 + az^2)
    amag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)

    # 2. Z-Axis Features (Vertical axis, primary vibration direction)
    az_mean = float(np.mean(az))
    az_std = float(np.std(az))
    az_min = float(np.min(az))
    az_max = float(np.max(az))
    az_p2p = az_max - az_min
    az_rms = float(np.sqrt(np.mean(az ** 2)))
    az_kurt = calculate_kurtosis(az)
    az_crest = (float(np.max(np.abs(az))) / az_rms) if az_rms > 1e-6 else 1.0
    az_energy = float(np.mean((az - 1.0) ** 2))

    # 3. Acceleration Magnitude Features
    amag_mean = float(np.mean(amag))
    amag_std = float(np.std(amag))
    amag_min = float(np.min(amag))
    amag_max = float(np.max(amag))
    amag_p2p = amag_max - amag_min
    amag_rms = float(np.sqrt(np.mean(amag ** 2)))
    amag_kurt = calculate_kurtosis(amag)

    # 4. Planar (X & Y) Stability Features (Lateral roll and pitch dynamics)
    ax_std = float(np.std(ax))
    ax_p2p = float(np.max(ax) - np.min(ax))
    ay_std = float(np.std(ay))
    ay_p2p = float(np.max(ay) - np.min(ay))

    # 5. Temporal Asymmetry & Waveform Shape
    # Check if cavity drop happens before rebound peak (pothole signature)
    min_idx = int(np.argmin(az))
    max_idx = int(np.argmax(az))
    drop_before_rise = 1.0 if min_idx < max_idx else 0.0

    # Ratio of drop magnitude below 1.0g to crest magnitude above 1.0g
    neg_dev = abs(az_min - 1.0)
    pos_dev = abs(az_max - 1.0)
    z_min_max_ratio = float(neg_dev / (pos_dev + 1e-6))

    # 6. Gyroscope Features (if available)
    if gx is not None and gy is not None and gz is not None and len(gx) == n_samples:
        gx = np.nan_to_num(np.asarray(gx, dtype=np.float64), nan=0.0)
        gy = np.nan_to_num(np.asarray(gy, dtype=np.float64), nan=0.0)
        gz = np.nan_to_num(np.asarray(gz, dtype=np.float64), nan=0.0)
        g_mag = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2)
        gyro_mag_mean = float(np.mean(g_mag))
    else:
        gyro_mag_mean = 0.0

    features = {
        "az_mean": az_mean,
        "az_std": az_std,
        "az_min": az_min,
        "az_max": az_max,
        "az_peak_to_peak": az_p2p,
        "az_rms": az_rms,
        "az_kurtosis": az_kurt,
        "az_crest_factor": az_crest,
        "az_energy": az_energy,
        "amag_mean": amag_mean,
        "amag_std": amag_std,
        "amag_min": amag_min,
        "amag_max": amag_max,
        "amag_peak_to_peak": amag_p2p,
        "amag_rms": amag_rms,
        "amag_kurtosis": amag_kurt,
        "ax_std": ax_std,
        "ax_peak_to_peak": ax_p2p,
        "ay_std": ay_std,
        "ay_peak_to_peak": ay_p2p,
        "temporal_drop_before_rise": drop_before_rise,
        "z_min_max_ratio": z_min_max_ratio,
        "gyro_magnitude_mean": gyro_mag_mean
    }

    return features


def extract_features_vector(
    ax: np.ndarray,
    ay: np.ndarray,
    az: np.ndarray,
    gx: np.ndarray = None,
    gy: np.ndarray = None,
    gz: np.ndarray = None
) -> np.ndarray:
    """
    Extracts features and returns an ordered 1D numpy array matching FEATURE_NAMES.
    Guarantees deterministic feature ordering for Scikit-Learn estimators.
    """
    feat_dict = extract_features_from_arrays(ax, ay, az, gx, gy, gz)
    return np.array([feat_dict[name] for name in FEATURE_NAMES], dtype=np.float64)


def extract_windows_from_dataframe(
    df: pd.DataFrame,
    window_samples: int = 100,
    step_samples: int = 50,
    sampling_rate_hz: int = 100
) -> pd.DataFrame:
    """
    Slices a continuous sensor stream DataFrame into sliding windows and extracts
    features for each window.

    Expected DataFrame columns:
        'ax', 'ay', 'az' (required)
        'gx', 'gy', 'gz' (optional)
        'label' (optional, preserved if present)
        'ride_id' (optional, preserved for group splitting)
        'lat', 'lon' (optional, window midpoint coordinate preserved)

    Returns:
        pd.DataFrame where each row is an extracted feature window.
    """
    required_cols = {"ax", "ay", "az"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame is missing required accelerometer columns: {missing}")

    records = []
    n_rows = len(df)
    has_gyro = {"gx", "gy", "gz"}.issubset(set(df.columns))
    has_label = "label" in df.columns
    has_ride = "ride_id" in df.columns
    has_gps = "lat" in df.columns and "lon" in df.columns

    for start_idx in range(0, n_rows - window_samples + 1, step_samples):
        end_idx = start_idx + window_samples
        chunk = df.iloc[start_idx:end_idx]

        ax = chunk["ax"].to_numpy()
        ay = chunk["ay"].to_numpy()
        az = chunk["az"].to_numpy()
        gx = chunk["gx"].to_numpy() if has_gyro else None
        gy = chunk["gy"].to_numpy() if has_gyro else None
        gz = chunk["gz"].to_numpy() if has_gyro else None

        features = extract_features_from_arrays(ax, ay, az, gx, gy, gz)

        # Retain metadata for training / tracking
        if has_label:
            # Assign most frequent label in window
            labels = chunk["label"].dropna()
            features["label"] = labels.mode()[0] if not labels.empty else "NORMAL_ROAD"
        if has_ride:
            features["ride_id"] = chunk["ride_id"].iloc[0]
        if has_gps:
            mid_idx = start_idx + (window_samples // 2)
            features["lat"] = float(df["lat"].iloc[mid_idx])
            features["lon"] = float(df["lon"].iloc[mid_idx])
        if "timestamp_ms" in chunk.columns:
            features["window_start_ms"] = int(chunk["timestamp_ms"].iloc[0])
            features["window_end_ms"] = int(chunk["timestamp_ms"].iloc[-1])

        records.append(features)

    return pd.DataFrame(records)
