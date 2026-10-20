"""
Unit Tests for Preprocessing and Feature Extraction
===================================================
Tests feature extraction mathematical validity, edge case handling (NaNs, flatlines),
and sliding window consistency.
"""

import pytest
import numpy as np
import pandas as pd
from ml.preprocess import (
    extract_features_from_arrays,
    extract_features_vector,
    extract_windows_from_dataframe,
    get_feature_names,
    calculate_kurtosis,
    FEATURE_NAMES
)


def test_feature_names_order_and_count():
    names = get_feature_names()
    assert isinstance(names, list)
    assert len(names) == len(FEATURE_NAMES)
    assert "az_kurtosis" in names
    assert "az_peak_to_peak" in names
    assert "temporal_drop_before_rise" in names


def test_calculate_kurtosis_normal_vs_impulse():
    # Normal distribution kurtosis is around 3.0
    np.random.seed(42)
    gaussian = np.random.normal(0, 1, 1000)
    k_gauss = calculate_kurtosis(gaussian)
    assert 2.5 <= k_gauss <= 3.5

    # Sharp impulse (pothole shock) produces high kurtosis (> 5.0)
    impulse = np.zeros(100)
    impulse[50] = 5.0  # Sharp spike
    k_impulse = calculate_kurtosis(impulse)
    assert k_impulse > 10.0


def test_extract_features_valid_arrays():
    n_samples = 100
    ax = np.zeros(n_samples)
    ay = np.zeros(n_samples)
    az = np.ones(n_samples) * 1.0  # Steady 1g

    features = extract_features_from_arrays(ax, ay, az)

    assert isinstance(features, dict)
    assert len(features) == len(FEATURE_NAMES)
    assert pytest.approx(features["az_mean"], abs=1e-3) == 1.0
    assert pytest.approx(features["az_std"], abs=1e-3) == 0.0
    assert pytest.approx(features["az_peak_to_peak"], abs=1e-3) == 0.0
    assert pytest.approx(features["az_rms"], abs=1e-3) == 1.0
    assert pytest.approx(features["az_energy"], abs=1e-3) == 0.0


def test_extract_features_nan_and_inf_handling():
    n_samples = 100
    # Dirty input with NaNs and Infs
    ax = np.full(n_samples, np.nan)
    ay = np.full(n_samples, np.inf)
    az = np.ones(n_samples)
    az[10] = np.nan
    az[20] = -np.inf

    features = extract_features_from_arrays(ax, ay, az)
    assert not np.isnan(features["az_mean"])
    assert not np.isinf(features["az_mean"])
    assert not np.isnan(features["amag_rms"])


def test_extract_features_vector_format():
    ax = np.random.normal(0, 0.05, 100)
    ay = np.random.normal(0, 0.05, 100)
    az = np.random.normal(1.0, 0.1, 100)

    vec = extract_features_vector(ax, ay, az)
    assert isinstance(vec, np.ndarray)
    assert vec.ndim == 1
    assert len(vec) == len(FEATURE_NAMES)


def test_extract_windows_from_dataframe():
    # 250 samples: with window=100 and step=50 -> 4 windows
    data = {
        "timestamp_ms": np.arange(250) * 10,
        "ax": np.random.normal(0, 0.02, 250),
        "ay": np.random.normal(0, 0.02, 250),
        "az": np.random.normal(1.0, 0.05, 250),
        "lat": np.full(250, 18.5204),
        "lon": np.full(250, 73.8567),
        "ride_id": ["RIDE_01"] * 250,
        "label": ["NORMAL_ROAD"] * 250
    }
    df = pd.DataFrame(data)
    windows_df = extract_windows_from_dataframe(df, window_samples=100, step_samples=50)

    assert len(windows_df) == 4
    assert "az_mean" in windows_df.columns
    assert "label" in windows_df.columns
    assert windows_df["ride_id"].iloc[0] == "RIDE_01"
    assert pytest.approx(windows_df["lat"].iloc[0], abs=1e-4) == 18.5204
