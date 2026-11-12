import os
import time
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit

from backend.app.ml.features import (
    prepare_features,
    FEATURE_COLUMNS,
    InsufficientDataError
)
from backend.app.services.market_service import get_stock_history_df, normalize_symbol, get_stock_quote

ARTIFACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "artifacts"))
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# In-memory model cache to avoid expensive retraining on every API request
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_VALIDITY_SECONDS = 86400  # 24 hours


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    current_prices: np.ndarray
) -> Dict[str, float]:
    """
    Computes financial machine learning metrics:
    - MAE: Mean Absolute Error in price units (INR)
    - RMSE: Root Mean Squared Error
    - Directional Accuracy: Percentage of correctly predicted price movement directions.
    """
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # Directional Accuracy
    actual_change = y_true - current_prices
    predicted_change = y_pred - current_prices

    # Avoid zero division and sign mismatches
    actual_sign = np.sign(actual_change)
    pred_sign = np.sign(predicted_change)

    # Consider 0 change as match only if predicted is also 0
    correct_direction = (actual_sign == pred_sign)
    directional_accuracy = float(np.mean(correct_direction) * 100.0)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "directional_accuracy": round(directional_accuracy, 2),
        "sample_count": len(y_true)
    }


def run_walk_forward_validation(
    model_class,
    model_params: dict,
    X: pd.DataFrame,
    y: pd.Series,
    current_prices: pd.Series,
    n_splits: int = 3
) -> Dict[str, float]:
    """
    Performs expanding-window walk-forward validation (TimeSeriesSplit).
    Guarantees strict forward-only testing with zero lookahead bias.
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    all_true = []
    all_pred = []
    all_curr = []

    for train_idx, val_idx in tscv.split(X):
        X_train_f, X_val_f = X.iloc[train_idx], X.iloc[val_idx]
        y_train_f, y_val_f = y.iloc[train_idx], y.iloc[val_idx]
        curr_val_f = current_prices.iloc[val_idx]

        fold_model = model_class(**model_params)
        fold_model.fit(X_train_f, y_train_f)
        fold_preds = fold_model.predict(X_val_f)

        all_true.extend(y_val_f.values)
        all_pred.extend(fold_preds)
        all_curr.extend(curr_val_f.values)

    return evaluate_predictions(np.array(all_true), np.array(all_pred), np.array(all_curr))


def train_models_for_symbol(symbol: str, period: str = "2y") -> Dict[str, Any]:
    """
    Trains Random Forest, XGBoost, and Persistence Baseline on historical data
    with strict chronological train/test split and serializes artifacts to disk.
    """
    norm_sym = normalize_symbol(symbol)
    df_raw, is_demo, data_source = get_stock_history_df(norm_sym, period=period, interval="1d")

    X, y, latest_features, full_df = prepare_features(df_raw)
    current_prices = full_df["close"]

    # 1. Strict Chronological Split (80% Train, 20% Test) - NEVER SHUFFLED
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    curr_test = current_prices.iloc[split_idx:]

    train_dates = f"{full_df['timestamp'].iloc[0]} to {full_df['timestamp'].iloc[split_idx-1]}"
    test_dates = f"{full_df['timestamp'].iloc[split_idx]} to {full_df['timestamp'].iloc[-1]}"

    # --- Model 1: Persistence Baseline (Random Walk Benchmark) ---
    baseline_test_preds = curr_test.values
    baseline_metrics = evaluate_predictions(y_test.values, baseline_test_preds, curr_test.values)

    # --- Model 2: Random Forest Regressor ---
    rf_params = {"n_estimators": 100, "max_depth": 6, "min_samples_split": 5, "random_state": 42, "n_jobs": -1}
    rf_model = RandomForestRegressor(**rf_params)
    rf_model.fit(X_train, y_train)
    rf_test_preds = rf_model.predict(X_test)
    rf_metrics = evaluate_predictions(y_test.values, rf_test_preds, curr_test.values)
    rf_wf_metrics = run_walk_forward_validation(RandomForestRegressor, rf_params, X, y, current_prices)

    # Feature Importance (Random Forest)
    rf_importances = dict(sorted(
        zip(FEATURE_COLUMNS, [round(float(v), 4) for v in rf_model.feature_importances_]),
        key=lambda item: item[1],
        reverse=True
    ))

    # --- Model 3: XGBoost Regressor ---
    xgb_params = {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "n_jobs": -1
    }
    xgb_model = XGBRegressor(**xgb_params)
    xgb_model.fit(X_train, y_train)
    xgb_test_preds = xgb_model.predict(X_test)
    xgb_metrics = evaluate_predictions(y_test.values, xgb_test_preds, curr_test.values)
    xgb_wf_metrics = run_walk_forward_validation(XGBRegressor, xgb_params, X, y, current_prices)

    # Feature Importance (XGBoost)
    xgb_importances = dict(sorted(
        zip(FEATURE_COLUMNS, [round(float(v), 4) for v in xgb_model.feature_importances_]),
        key=lambda item: item[1],
        reverse=True
    ))

    # --- Persistence Serialization ---
    clean_sym_name = norm_sym.replace("^", "").replace(".", "_")
    rf_path = os.path.join(ARTIFACTS_DIR, f"{clean_sym_name}_rf.joblib")
    xgb_path = os.path.join(ARTIFACTS_DIR, f"{clean_sym_name}_xgb.joblib")
    meta_path = os.path.join(ARTIFACTS_DIR, f"{clean_sym_name}_meta.json")

    joblib.dump(rf_model, rf_path)
    joblib.dump(xgb_model, xgb_path)

    metadata = {
        "symbol": norm_sym,
        "trained_at": time.time(),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "train_date_range": train_dates,
        "test_date_range": test_dates,
        "baseline_metrics": baseline_metrics,
        "rf_metrics": rf_metrics,
        "rf_wf_metrics": rf_wf_metrics,
        "rf_importances": rf_importances,
        "xgb_metrics": xgb_metrics,
        "xgb_wf_metrics": xgb_wf_metrics,
        "xgb_importances": xgb_importances,
        "is_demo": is_demo,
        "data_source": data_source
    }

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    cached_entry = {
        "rf_model": rf_model,
        "xgb_model": xgb_model,
        "metadata": metadata,
        "latest_features": latest_features,
        "current_price": float(current_prices.iloc[-1]),
        "timestamp": time.time()
    }
    _MEMORY_CACHE[norm_sym] = cached_entry

    return cached_entry


def get_trained_models(symbol: str, force_retrain: bool = False) -> Dict[str, Any]:
    """
    Returns pre-trained models from memory cache or disk.
    If not found or force_retrain is True, trains models and caches them.
    Guarantees no redundant retraining on every API request.
    """
    norm_sym = normalize_symbol(symbol)
    clean_sym_name = norm_sym.replace("^", "").replace(".", "_")

    # 1. Check in-memory cache
    if not force_retrain and norm_sym in _MEMORY_CACHE:
        entry = _MEMORY_CACHE[norm_sym]
        if time.time() - entry["timestamp"] < CACHE_VALIDITY_SECONDS:
            return entry

    # 2. Check disk artifacts
    rf_path = os.path.join(ARTIFACTS_DIR, f"{clean_sym_name}_rf.joblib")
    xgb_path = os.path.join(ARTIFACTS_DIR, f"{clean_sym_name}_xgb.joblib")
    meta_path = os.path.join(ARTIFACTS_DIR, f"{clean_sym_name}_meta.json")

    if not force_retrain and os.path.exists(rf_path) and os.path.exists(xgb_path) and os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)

            if time.time() - meta.get("trained_at", 0) < CACHE_VALIDITY_SECONDS:
                rf_model = joblib.load(rf_path)
                xgb_model = joblib.load(xgb_path)

                # Fetch latest single day features for forward inference
                df_raw, is_demo, _ = get_stock_history_df(norm_sym, period="3mo", interval="1d")
                _, _, latest_features, full_df = prepare_features(df_raw)

                entry = {
                    "rf_model": rf_model,
                    "xgb_model": xgb_model,
                    "metadata": meta,
                    "latest_features": latest_features,
                    "current_price": float(full_df["close"].iloc[-1]),
                    "timestamp": time.time()
                }
                _MEMORY_CACHE[norm_sym] = entry
                return entry
        except Exception:
            # Fall back to retraining if disk artifact read failed
            pass

    # 3. Otherwise train and cache
    return train_models_for_symbol(norm_sym)


def predict_next_day(symbol: str) -> Dict[str, Any]:
    """
    Performs out-of-sample forward inference using serialized models.
    Returns Random Forest, XGBoost, and Baseline predictions.
    """
    entry = get_trained_models(symbol)
    rf_model = entry["rf_model"]
    xgb_model = entry["xgb_model"]
    metadata = entry["metadata"]
    features = entry["latest_features"]
    curr_price = entry["current_price"]

    # Generate model predictions for t+1
    pred_rf = float(rf_model.predict(features)[0])
    pred_xgb = float(xgb_model.predict(features)[0])
    pred_baseline = float(curr_price)  # Random Walk / Persistence

    def build_pred_item(pred_p, metrics):
        chg = pred_p - curr_price
        pct = (chg / curr_price * 100) if curr_price > 0 else 0.0
        if abs(pct) < 0.15:
            direction = "FLAT"
        elif pct > 0:
            direction = "UP"
        else:
            direction = "DOWN"

        return {
            "predicted_price": round(pred_p, 2),
            "expected_change": round(chg, 2),
            "expected_change_percent": round(pct, 2),
            "predicted_direction": direction,
            "model_mae": metrics["mae"],
            "directional_accuracy_hist": metrics["directional_accuracy"]
        }

    rf_result = build_pred_item(pred_rf, metadata["rf_metrics"])
    xgb_result = build_pred_item(pred_xgb, metadata["xgb_metrics"])
    baseline_result = build_pred_item(pred_baseline, metadata["baseline_metrics"])

    # Consensus prediction: ensemble average
    consensus_price = round((pred_rf + pred_xgb) / 2.0, 2)
    consensus_chg = consensus_price - curr_price
    consensus_pct = (consensus_chg / curr_price * 100) if curr_price > 0 else 0.0

    if abs(consensus_pct) < 0.15:
        consensus_direction = "FLAT"
    elif consensus_pct > 0:
        consensus_direction = "UP"
    else:
        consensus_direction = "DOWN"

    # Confidence calculation based on directional agreement and historical test accuracy
    agreement = (rf_result["predicted_direction"] == xgb_result["predicted_direction"])
    avg_da = (rf_result["directional_accuracy_hist"] + xgb_result["directional_accuracy_hist"]) / 2.0

    if agreement and avg_da >= 55.0:
        confidence = "HIGH"
    elif agreement or avg_da >= 50.0:
        confidence = "MODERATE"
    else:
        confidence = "LOW"

    return {
        "symbol": metadata["symbol"],
        "current_price": round(curr_price, 2),
        "as_of_date": time.strftime("%Y-%m-%d"),
        "target_date": "Next Trading Session (t+1)",
        "predictions": {
            "random_forest": rf_result,
            "xgboost": xgb_result,
            "persistence_baseline": baseline_result
        },
        "consensus_predicted_price": consensus_price,
        "consensus_predicted_direction": consensus_direction,
        "confidence_level": confidence,
        "data_source": metadata.get("data_source", "live_api"),
        "is_demo": metadata.get("is_demo", False)
    }

