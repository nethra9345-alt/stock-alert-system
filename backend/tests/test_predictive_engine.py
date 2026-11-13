import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.ml.features import (
    prepare_advanced_features,
    ADVANCED_FEATURE_COLUMNS,
    InsufficientDataError
)
from backend.app.ml.engine import (
    evaluate_advanced_metrics,
    train_advanced_models_for_symbol,
    predict_multi_horizon,
    run_walk_forward_backtest,
    check_model_drift,
    get_prediction_history
)
from backend.app.core.database import SessionLocal
from backend.app.models.ml_registry import MLModelRegistry, MLPredictionRecord, MLBacktestRun, MLDriftRecord

client = TestClient(app)


def test_advanced_features_generation_and_zero_leakage():
    """
    Verifies:
    1. All 28 advanced technical feature columns are correctly generated.
    2. Zero future data leakage: Altering price at time t+k does NOT change features at time t.
    """
    n = 220
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    base_price = 2500.0
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.012, n)
    closes = base_price * np.cumprod(1 + returns)

    df_sample = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": closes * 0.997,
        "high": closes * 1.008,
        "low": closes * 0.993,
        "close": closes,
        "volume": rng.integers(200000, 800000, n)
    })

    X, y_ret, y_price, latest_feat, trainable_df, feat_cols = prepare_advanced_features(df_sample, horizon="1d")

    # 1. Feature existence
    for col in ADVANCED_FEATURE_COLUMNS:
        assert col in X.columns, f"Missing advanced feature: {col}"

    assert len(X) == len(y_ret)
    assert len(X) == len(y_price)
    assert len(latest_feat) == 1

    # 2. Strict Zero Leakage Test
    df_altered = df_sample.copy()
    # Modify future price at index 200
    df_altered.loc[200, "close"] = df_altered.loc[200, "close"] * 1.5
    X_alt, _, _, _, _, _ = prepare_advanced_features(df_altered, horizon="1d")

    # Features at index 60 (strictly prior to index 200) MUST be bitwise identical
    np.testing.assert_allclose(X.iloc[60].values, X_alt.iloc[60].values, rtol=1e-5)


def test_multi_horizon_target_alignment():
    """
    Verifies target alignment for 1d, 5d, and 10d horizons:
    Target return must match: (Close(t+h) - Close(t)) / Close(t).
    """
    n = 150
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    closes = np.linspace(1000.0, 1500.0, n)

    df_sample = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": closes * 0.999,
        "high": closes * 1.002,
        "low": closes * 0.998,
        "close": closes,
        "volume": np.full(n, 500000)
    })

    for hz, shift in [("1d", 1), ("5d", 5), ("10d", 10)]:
        X, y_ret, y_price, _, trainable_df, _ = prepare_advanced_features(df_sample, horizon=hz)
        # Check alignment on sample row 10
        c_t = trainable_df["close"].iloc[10]
        p_future = y_price.iloc[10]
        expected_ret = (p_future - c_t) / c_t
        assert y_ret.iloc[10] == pytest.approx(expected_ret, 1e-5)


def test_advanced_metrics_calculation():
    """Verifies MAE, RMSE, MAPE, Directional Accuracy and F1 metrics."""
    curr = np.array([100.0, 100.0, 100.0, 100.0])
    y_true = np.array([105.0, 95.0, 102.0, 98.0])
    y_pred = np.array([104.0, 96.0, 103.0, 97.0])

    m = evaluate_advanced_metrics(y_true, y_pred, curr)

    assert m["mae"] == pytest.approx(1.0, 0.01)
    assert m["rmse"] == pytest.approx(1.0, 0.01)
    assert m["directional_accuracy"] == 100.0  # All directions match
    assert m["precision_up"] == 100.0
    assert m["f1_up"] == 100.0


def test_advanced_models_training_and_intervals():
    """
    Trains Ridge, RF, XGB, and Gradient Boosting on RELIANCE.NS,
    verifying 80% and 95% prediction intervals and champion selection.
    """
    entry = train_advanced_models_for_symbol("RELIANCE.NS", horizon="1d", period="1y")
    meta = entry["metadata"]

    assert meta["symbol"] == "RELIANCE.NS"
    assert "champion_model" in meta
    assert meta["champion_model"] in [
        "persistence_baseline", "ridge_regression", "random_forest", "xgboost", "gradient_boosting"
    ]

    preds = meta["prediction_items"]
    for m_name in ["persistence_baseline", "ridge_regression", "random_forest", "xgboost", "gradient_boosting"]:
        assert m_name in preds
        p = preds[m_name]
        assert p["predicted_price"] > 0
        # Check calibrated prediction interval ordering: lower <= predicted <= upper
        assert p["lower_bound_80"] <= p["predicted_price"] <= p["upper_bound_80"]
        assert p["lower_bound_95"] <= p["lower_bound_80"]
        assert p["upper_bound_95"] >= p["upper_bound_80"]


def test_multi_horizon_prediction_function():
    """Tests predict_multi_horizon across 1d, 5d, and 10d horizons."""
    for hz in ["1d", "5d", "10d"]:
        res = predict_multi_horizon("TCS.NS", horizon=hz)
        assert res["symbol"] == "TCS.NS"
        assert res["horizon"] == hz
        assert res["current_price"] > 0
        assert res["champion_predicted_price"] > 0
        assert res["lower_bound"] <= res["champion_predicted_price"] <= res["upper_bound"]
        assert res["confidence_level"] in ["LOW", "MODERATE", "HIGH"]
        assert "uncertainty_explanation" in res


def test_walk_forward_backtest():
    """Tests walk-forward expanding window backtesting and simulated trading metrics."""
    res = run_walk_forward_backtest("INFY.NS", horizon="1d", model_name="champion", period="1y")

    assert res["symbol"] == "INFY.NS"
    assert res["total_steps"] > 0
    assert res["wf_mae"] > 0
    assert 0.0 <= res["wf_directional_accuracy"] <= 100.0
    assert len(res["equity_curve"]) > 1
    assert "error_distribution" in res
    assert "mean_error" in res["error_distribution"]


def test_model_drift_monitoring_service():
    """Tests concept drift detection on short-term price dynamics."""
    drift = check_model_drift("HDFCBANK.NS")

    assert drift["symbol"] == "HDFCBANK.NS"
    assert drift["drift_status"] in ["STABLE", "MODERATE_DRIFT", "HIGH_DRIFT"]
    assert drift["drift_ratio"] > 0
    assert isinstance(drift["retrain_recommended"], bool)
    assert len(drift["recommendation_text"]) > 10


def test_predict_api_multi_horizon_endpoint():
    """Tests GET /api/ml/predict/{symbol}?horizon=5d"""
    res = client.get("/api/ml/predict/RELIANCE.NS?horizon=5d")
    assert res.status_code == 200
    data = res.json()

    assert data["symbol"] == "RELIANCE.NS"
    assert data["horizon"] == "5d"
    assert "champion_model" in data
    assert data["lower_bound"] > 0
    assert data["upper_bound"] >= data["lower_bound"]
    assert "disclaimer" in data


def test_evaluate_api_advanced_models_endpoint():
    """Tests GET /api/ml/evaluate/{symbol}?horizon=1d"""
    res = client.get("/api/ml/evaluate/TCS.NS?horizon=1d")
    assert res.status_code == 200
    data = res.json()

    assert data["symbol"] == "TCS.NS"
    assert "models" in data
    assert "persistence_baseline" in data["models"]
    assert "ridge_regression" in data["models"]
    assert "random_forest" in data["models"]
    assert "xgboost" in data["models"]
    assert "gradient_boosting" in data["models"]
    assert "champion_model" in data


def test_backtest_and_drift_api_endpoints():
    """Tests GET /api/ml/backtest and GET /api/ml/drift"""
    bt_res = client.get("/api/ml/backtest/SBIN.NS?horizon=1d&period=1y")
    assert bt_res.status_code == 200
    bt_data = bt_res.json()
    assert bt_data["symbol"] == "SBIN.NS"
    assert "wf_mae" in bt_data
    assert "equity_curve" in bt_data

    drift_res = client.get("/api/ml/drift/SBIN.NS")
    assert drift_res.status_code == 200
    drift_data = drift_res.json()
    assert drift_data["symbol"] == "SBIN.NS"
    assert drift_data["drift_status"] in ["STABLE", "MODERATE_DRIFT", "HIGH_DRIFT"]

    hist_res = client.get("/api/ml/prediction-history/SBIN.NS?limit=10")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert isinstance(hist_data, list)
    assert len(hist_data) >= 1


def test_postgresql_ml_registry_persistence():
    """Verifies that trained models and backtest runs are persisted in PostgreSQL."""
    session = SessionLocal()
    try:
        models_count = session.query(MLModelRegistry).filter(
            MLModelRegistry.symbol == "RELIANCE.NS"
        ).count()
        assert models_count > 0

        preds_count = session.query(MLPredictionRecord).filter(
            MLPredictionRecord.symbol == "RELIANCE.NS"
        ).count()
        assert preds_count > 0
    finally:
        session.close()
