"""
RoadGuard AI - Model Training and Evaluation Pipeline
======================================================
Trains and evaluates a Random Forest classifier for road hazard classification.

Key Methodological Guarantees:
------------------------------
1. Group-Based Splitting:
   - Uses `GroupShuffleSplit` on `ride_id` so that an entire ride is either in the training
     set or in the testing set. Overlapping windows from the same ride NEVER leak into both.
2. Identical Feature Extraction:
   - Uses `ml.preprocess` to extract the exact canonical feature vector.
3. Transparent Performance Reporting:
   - Computes Accuracy, Macro Precision, Macro Recall, Macro F1, and per-class metrics.
   - Plots and saves confusion matrix and feature importance ranking.
4. Comprehensive Artifact Packaging:
   - Saves `road_model.joblib` and `model_metadata.json` with class labels, feature order,
     hyperparameters, metrics, and dataset origin disclaimer.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_recall_fscore_support
)

# Add parent directory to path so imports work cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.preprocess import (
    extract_windows_from_dataframe,
    get_feature_names,
    FEATURE_NAMES
)

TARGET_CLASSES = ["NORMAL_ROAD", "POTHOLE", "SPEED_BREAKER", "ROUGH_ROAD"]


def validate_dataset(df: pd.DataFrame) -> bool:
    """Validates raw sensor dataset schema and label integrity."""
    required_cols = {"timestamp_ms", "ax", "ay", "az", "label"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    if "ride_id" not in df.columns:
        print("[Warning] 'ride_id' column not found. Adding default ride identifier.")
        df["ride_id"] = "RIDE_DEFAULT"

    # Check labels
    unique_labels = set(df["label"].dropna().unique())
    invalid_labels = unique_labels - set(TARGET_CLASSES)
    if invalid_labels:
        print(f"[Warning] Found unrecognized labels: {invalid_labels}. These will be filtered.")
        df = df[df["label"].isin(TARGET_CLASSES)]

    counts = df["label"].value_counts()
    print("\n--- Dataset Summary ---")
    print(f"Total Raw Rows: {len(df):,}")
    print(f"Distinct Rides: {df['ride_id'].nunique()}")
    print("Class Sample Counts:")
    for lbl, cnt in counts.items():
        print(f"  • {lbl:<15}: {cnt:,} samples")
    print("------------------------\n")
    return True


def train_and_evaluate(
    dataset_csv: str,
    output_dir: str = "models",
    n_estimators: int = 100,
    test_size: float = 0.25,
    random_state: int = 42
):
    """Loads dataset, extracts features, trains Random Forest, evaluates, and persists."""
    print(f"[Trainer] Loading dataset: {dataset_csv}")
    if not os.path.exists(dataset_csv):
        raise FileNotFoundError(f"Dataset not found at {dataset_csv}. Run simulate_sensors.py or collect_data.py first.")

    raw_df = pd.read_csv(dataset_csv)
    validate_dataset(raw_df)

    # 1. Windowing and Feature Extraction
    print("[Trainer] Extracting features from sliding windows (100 samples/window, 50% step)...")
    windows_df = extract_windows_from_dataframe(
        raw_df,
        window_samples=100,
        step_samples=50
    )
    print(f"[Trainer] Extracted {len(windows_df):,} feature windows.")

    # Filter to valid classes only
    windows_df = windows_df[windows_df["label"].isin(TARGET_CLASSES)].reset_index(drop=True)

    # 2. Prepare Feature Matrix X and Target Vector y
    feature_cols = get_feature_names()
    X = windows_df[feature_cols].to_numpy()
    y = windows_df["label"].to_numpy()
    groups = windows_df["ride_id"].to_numpy()

    print(f"[Trainer] Feature Matrix shape: {X.shape}")

    # 3. Group-Based Train/Test Split (Preserves entire rides for realistic out-of-sample test)
    n_groups = len(np.unique(groups))
    if n_groups > 1:
        print(f"[Trainer] Performing GroupShuffleSplit across {n_groups} rides (test_size={test_size})...")
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(gss.split(X, y, groups=groups))
    else:
        print("[Warning] Only 1 ride_id present. Falling back to stratified random split.")
        from sklearn.model_selection import train_test_split
        train_idx, test_idx = train_test_split(
            np.arange(len(y)), test_size=test_size, stratify=y, random_state=random_state
        )

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    train_rides = sorted(list(set(groups[train_idx])))
    test_rides = sorted(list(set(groups[test_idx])))
    print(f"[Trainer] Training set: {len(X_train)} windows (Rides: {train_rides})")
    print(f"[Trainer] Testing set:  {len(X_test)} windows (Rides: {test_rides})")

    # 4. Train Random Forest Classifier
    print(f"\n[Trainer] Training RandomForestClassifier (trees={n_estimators}, max_depth=12, class_weight='balanced')...")
    rf_model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    print("[Trainer] Model training completed.")

    # 5. Evaluate on Unseen Test Rides
    y_pred = rf_model.predict(X_test)
    y_pred_proba = rf_model.predict_proba(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)

    # Detailed Classification Report
    cls_report = classification_report(y_test, y_pred, target_names=rf_model.classes_, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=rf_model.classes_)

    print("\n================ MODEL EVALUATION REPORT ================")
    print(f"Overall Accuracy:  {acc * 100:.2f}%")
    print(f"Macro Precision:   {p_macro * 100:.2f}%")
    print(f"Macro Recall:      {r_macro * 100:.2f}%")
    print(f"Macro F1-Score:    {f1_macro * 100:.2f}%")
    print("\nPer-Class Performance:")
    print(f"{'Class':<16} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("-" * 64)
    for cls_name in rf_model.classes_:
        metrics = cls_report.get(cls_name, {})
        print(f"{cls_name:<16} | {metrics.get('precision', 0)*100:>9.2f}% | "
              f"{metrics.get('recall', 0)*100:>9.2f}% | {metrics.get('f1-score', 0)*100:>9.2f}% | "
              f"{int(metrics.get('support', 0)):>8}")
    print("=========================================================\n")

    # Check for confusion between Potholes, Speed Breakers, and Rough Road
    print("Confusion Matrix:")
    print(f"Classes: {list(rf_model.classes_)}")
    print(cm)
    print("---------------------------------------------------------")

    # 6. Feature Importances
    importances = rf_model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    top_features = []
    print("\nTop 8 Most Discriminative Features:")
    for rank in range(min(8, len(sorted_idx))):
        idx = sorted_idx[rank]
        feat_name = feature_cols[idx]
        feat_imp = float(importances[idx])
        top_features.append({"feature": feat_name, "importance": round(feat_imp, 4)})
        print(f"  {rank+1}. {feat_name:<26}: {feat_imp*100:.2f}%")

    # 7. Save Artifacts
    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "road_model.joblib")
    joblib.dump(rf_model, model_path)
    print(f"\n[Artifacts] Saved trained model to: {model_path}")

    # Metadata
    is_synthetic = "SYNTHETIC" in str(raw_df.get("data_source", "").iloc[0] if "data_source" in raw_df.columns else "")
    metadata = {
        "model_type": "RandomForestClassifier",
        "n_estimators": n_estimators,
        "classes": list(rf_model.classes_),
        "feature_names": feature_cols,
        "n_features": len(feature_cols),
        "window_duration_seconds": 1.0,
        "sampling_rate_hz": 100,
        "created_at": datetime.now().isoformat(),
        "trained_on_dataset": dataset_csv,
        "dataset_type": "SYNTHETIC_SIMULATION" if is_synthetic else "REAL_HARDWARE",
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_rides": train_rides,
        "test_rides": test_rides,
        "metrics": {
            "accuracy": round(acc, 4),
            "macro_precision": round(p_macro, 4),
            "macro_recall": round(r_macro, 4),
            "macro_f1": round(f1_macro, 4)
        },
        "per_class_metrics": {c: {k: round(v, 4) for k, v in cls_report[c].items()} for c in rf_model.classes_},
        "confusion_matrix": cm.tolist(),
        "top_features": top_features,
        "disclaimer": "Evaluated on calibrated synthetic test rides. Genuine municipal accuracy requires vehicle field calibration."
    }

    metadata_path = os.path.join(output_dir, "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[Artifacts] Saved model metadata to: {metadata_path}")

    # 8. Generate and Save Confusion Matrix Visual Chart
    plot_path = os.path.join(output_dir, "confusion_matrix.png")
    fig, ax = plt.subplots(figsize=(6, 5), dpi=200)
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    classes = rf_model.classes_
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=classes, yticklabels=classes,
        title='RoadGuard AI - Confusion Matrix (Unseen Test Rides)',
        ylabel='True Label',
        xlabel='Predicted Label'
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Annotate numbers
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontweight="bold")
    plt.tight_layout()
    plt.savefig(plot_path, bbox_inches='tight')
    plt.close()
    print(f"[Artifacts] Saved confusion matrix visualization to: {plot_path}")

    return rf_model, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RoadGuard AI Model Trainer")
    parser.add_argument("--dataset", type=str, default="data/synthetic_demo_dataset.csv", help="Input labeled CSV")
    parser.add_argument("--output-dir", type=str, default="models", help="Directory to save model artifacts")
    parser.add_argument("--trees", type=int, default=100, help="Number of trees in Random Forest")
    parser.add_argument("--test-size", type=float, default=0.25, help="Test fraction (split by ride)")
    args = parser.parse_args()

    train_and_evaluate(
        dataset_csv=args.dataset,
        output_dir=args.output_dir,
        n_estimators=args.trees,
        test_size=args.test_size
    )
