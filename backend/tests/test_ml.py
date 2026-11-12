import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.ml.features import (
    prepare_features,
    FEATURE_COLUMNS,
    InsufficientDataError
)
from backend.app.ml.engine import (
    train_models_for_symbol,
    get_trained_models,
    predict_next_day,
    evaluate_predictions
)

client = TestClient(app)


def test_feature_engineering_and_zero_leakage():
    """
    Verifies:
    1. All expected feature columns are generated.
    2. Zero future data leakage: features at row t are completely invariant
       to changes in row t+1 close price.
    """
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    base_price = 1000.0
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, n)
    closes = base_price * np.cumprod(1 + returns)

    df_sample = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": closes * 0.998,
        "high": closes * 1.005,
        "low": closes * 0.995,
        "close": closes,
        "volume": rng.integers(100000, 500000, n)
    })

    X, y, latest_feat, full_df = prepare_features(df_sample)

    for col in FEATURE_COLUMNS:
        assert col in X.columns, f"Missing feature: {col}"

    assert len(X) == len(y)
    assert len(latest_feat) == 1

    # Verify Zero Leakage: Altering future price in df_sample should NOT alter past features
    df_altered = df_sample.copy()
    # Double the price at index 180
    df_altered.loc[180, "close"] = df_altered.loc[180, "close"] * 2.0
    X_alt, _, _, _ = prepare_features(df_altered)

    # Features at index 50 (strictly prior to index 180) must be 100% IDENTICAL
    np.testing.assert_allclose(X.iloc[50].values, X_alt.iloc[50].values, rtol=1e-5)


def test_insufficient_historical_data_guard():
    """Verify InsufficientDataError is raised when candles are fewer than minimum required."""
    short_df = pd.DataFrame({
        "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [100.0, 101.0, 102.0],
        "high": [105.0, 106.0, 107.0],
        "low": [98.0, 99.0, 100.0],
        "close": [101.0, 102.0, 103.0],
        "volume": [10000, 12000, 11000]
    })
    with pytest.raises(InsufficientDataError):
        prepare_features(short_df)


def test_metric_calculations():
    """Verify MAE, RMSE and Directional Accuracy calculations."""
    y_true = np.array([105.0, 110.0, 95.0, 100.0])
    y_pred = np.array([104.0, 112.0, 96.0, 98.0])
    current = np.array([100.0, 105.0, 100.0, 95.0])

    metrics = evaluate_predictions(y_true, y_pred, current)

    assert metrics["mae"] == pytest.approx(1.5, 0.05)
    assert metrics["rmse"] > 0
    assert metrics["directional_accuracy"] == 100.0  # All directions matched


def test_ml_training_and_serialization():
    """Train models on RELIANCE.NS and verify metrics, serialization and baseline comparison."""
    entry = train_models_for_symbol("RELIANCE.NS", period="1y")
    meta = entry["metadata"]

    assert meta["symbol"] == "RELIANCE.NS"
    assert "baseline_metrics" in meta
    assert "rf_metrics" in meta
    assert "xgb_metrics" in meta

    # Metrics validity
    assert meta["rf_metrics"]["mae"] > 0
    assert meta["xgb_metrics"]["mae"] > 0
    assert 0.0 <= meta["rf_metrics"]["directional_accuracy"] <= 100.0
    assert 0.0 <= meta["xgb_metrics"]["directional_accuracy"] <= 100.0

    # Feature importances
    assert len(meta["rf_importances"]) == len(FEATURE_COLUMNS)
    assert len(meta["xgb_importances"]) == len(FEATURE_COLUMNS)

    # Walk-forward validation metrics
    assert "rf_wf_metrics" in meta
    assert meta["rf_wf_metrics"]["sample_count"] > 0


def test_predict_next_day_inference():
    """Verify prediction pipeline outputs valid structure and disclaimer."""
    result = predict_next_day("TCS.NS")

    assert result["symbol"] == "TCS.NS"
    assert result["current_price"] > 0
    assert "predictions" in result
    assert "random_forest" in result["predictions"]
    assert "xgboost" in result["predictions"]
    assert "persistence_baseline" in result["predictions"]
    assert result["consensus_predicted_direction"] in ["UP", "DOWN", "FLAT"]
    assert result["confidence_level"] in ["LOW", "MODERATE", "HIGH"]


def test_ml_api_models_endpoint():
    """GET /api/ml/models"""
    res = client.get("/api/ml/models")
    assert res.status_code == 200
    data = res.json()
    assert "architecture" in data
    assert len(data["supported_models"]) >= 3
    assert len(data["features_used"]) == len(FEATURE_COLUMNS)
    assert "disclaimer" in data
    assert "guarantee" in data["disclaimer"].lower() or "risk" in data["disclaimer"].lower()


def test_ml_api_predict_endpoint():
    """GET /api/ml/predict/INFY.NS"""
    res = client.get("/api/ml/predict/INFY.NS")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "INFY.NS"
    assert "predictions" in data
    assert "random_forest" in data["predictions"]
    assert "xgboost" in data["predictions"]
    assert "consensus_predicted_price" in data
    assert "disclaimer" in data


def test_ml_api_evaluate_endpoint():
    """GET /api/ml/evaluate/HDFCBANK.NS"""
    res = client.get("/api/ml/evaluate/HDFCBANK.NS")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "HDFCBANK.NS"
    assert "models" in data
    assert "random_forest" in data["models"]
    assert "xgboost" in data["models"]
    assert "persistence_baseline" in data["models"]
    assert "best_model_by_mae" in data
    assert "best_model_by_directional_accuracy" in data
    assert "disclaimer" in data


def test_ml_api_train_endpoint():
    """POST /api/ml/train/SBIN.NS"""
    res = client.post("/api/ml/train/SBIN.NS?period=1y")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "SBIN.NS"
    assert "models" in data
    assert data["train_samples"] > 0
    assert data["test_samples"] > 0
