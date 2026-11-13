from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.ml import (
    StockPredictionResponse,
    ModelComparisonResponse,
    ModelEvaluationSummary,
    ModelMetric,
    ModelInfoResponse,
    BacktestResultResponse,
    ModelDriftResponse,
    PredictionHistoryItem,
    FINANCIAL_DISCLAIMER
)
from backend.app.ml.engine import (
    predict_next_day,
    get_trained_models,
    train_models_for_symbol,
    train_advanced_models_for_symbol,
    get_advanced_trained_models,
    predict_multi_horizon,
    run_walk_forward_backtest,
    check_model_drift,
    get_prediction_history
)
from backend.app.ml.features import (
    FEATURE_COLUMNS,
    ADVANCED_FEATURE_COLUMNS,
    InsufficientDataError
)
from backend.app.models.ml_registry import MLModelRegistry
from backend.app.services.market_service import normalize_symbol

router = APIRouter()


@router.get("/models", response_model=ModelInfoResponse)
def get_models_info():
    """Returns architecture overview, feature definitions, and validation methodology."""
    return ModelInfoResponse(
        architecture="Ensemble Multi-Horizon Quantitative Forecasting Engine (Stage 9)",
        supported_models=[
            "Persistence Baseline (Martingale benchmark: Return = 0)",
            "Ridge Regression (L2 Regularized linear model with StandardScaler)",
            "Random Forest Regressor (Non-linear bagging ensemble of 100 trees)",
            "XGBoost Regressor (Gradient-boosted decision trees with subsampling)",
            "HistGradientBoosting Regressor (Fast histogram-based gradient boosting)"
        ],
        features_used=FEATURE_COLUMNS,
        advanced_features_used=ADVANCED_FEATURE_COLUMNS,
        validation_strategy="Strict Chronological 80/20 Train/Test Split with Expanding TimeSeriesSplit Walk-Forward Validation",
        metrics=[
            "MAE (Mean Absolute Error in INR)",
            "RMSE (Root Mean Squared Error in INR)",
            "MAPE (Mean Absolute Percentage Error %)",
            "Directional Accuracy (% correctly predicted movement sign)",
            "Precision, Recall, F1 for directional movements"
        ],
        data_leakage_safeguards=[
            "Zero random shuffling on time series data",
            "Target alignment with strict forward shift: target is Return(t -> t+h)",
            "Features at time t strictly computed using observations <= t",
            "Past volume baseline excludes current session",
            "Feature scaling fit strictly on train split inside Pipeline",
            "Expanding window out-of-sample walk-forward backtesting",
            "Residual variance Gaussian calibration for prediction intervals"
        ],
        disclaimer=FINANCIAL_DISCLAIMER
    )


@router.get("/predict/{symbol}", response_model=StockPredictionResponse)
def get_prediction(
    symbol: str,
    horizon: str = Query("1d", description="Forecast horizon: 1d (next session), 5d (weekly), 10d (bi-weekly)"),
    db: Session = Depends(get_db)
):
    """
    Generates multi-horizon price and directional predictions using serialized models.
    Returns 80% and 95% calibrated prediction intervals, champion model, and consensus.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        # Fetch multi-horizon prediction
        multi_res = predict_multi_horizon(norm_sym, horizon=horizon, db=db)
        champ_model = multi_res["champion_model"]
        champ_pred = multi_res["predictions"][champ_model]

        # Fetch base single-day consensus predictions for backward compatibility
        base_pred = predict_next_day(norm_sym)

        # Merge prediction items
        merged_predictions = dict(base_pred["predictions"])
        for m_name, p_val in multi_res["predictions"].items():
            merged_predictions[m_name] = {
                "predicted_price": p_val["predicted_price"],
                "expected_change": round(p_val["predicted_price"] - multi_res["current_price"], 2),
                "expected_change_percent": p_val["predicted_return_pct"],
                "predicted_direction": p_val["predicted_direction"],
                "model_mae": p_val["model_mae"],
                "directional_accuracy_hist": p_val["directional_accuracy_hist"],
                "lower_bound_80": p_val["lower_bound_80"],
                "upper_bound_80": p_val["upper_bound_80"],
                "lower_bound_95": p_val["lower_bound_95"],
                "upper_bound_95": p_val["upper_bound_95"],
                "is_champion": p_val["is_champion"]
            }

        return StockPredictionResponse(
            symbol=norm_sym,
            current_price=multi_res["current_price"],
            as_of_date=multi_res["as_of_date"],
            target_date=multi_res["target_date"],
            predictions=merged_predictions,
            consensus_predicted_price=base_pred["consensus_predicted_price"],
            consensus_predicted_direction=base_pred["consensus_predicted_direction"],
            confidence_level=multi_res["confidence_level"],
            data_source=base_pred.get("data_source", "live_api"),
            is_demo=base_pred.get("is_demo", False),
            horizon=horizon,
            champion_model=champ_model,
            champion_predicted_price=champ_pred["predicted_price"],
            champion_predicted_direction=champ_pred["predicted_direction"],
            champion_predicted_return_pct=champ_pred["predicted_return_pct"],
            lower_bound=champ_pred["lower_bound_95"],
            upper_bound=champ_pred["upper_bound_95"],
            uncertainty_explanation=multi_res["uncertainty_explanation"],
            disclaimer=FINANCIAL_DISCLAIMER
        )
    except InsufficientDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to predict {symbol}: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error for {symbol}: {str(e)}"
        )


@router.get("/evaluate/{symbol}", response_model=ModelComparisonResponse)
def evaluate_models(
    symbol: str,
    horizon: str = Query("1d", description="Forecast horizon: 1d, 5d, 10d"),
    period: str = Query("2y", description="Historical period for training and evaluation"),
    db: Session = Depends(get_db)
):
    """
    Computes rigorous model comparison across Persistence Baseline, Ridge Regression,
    Random Forest, XGBoost, and Gradient Boosting on stationary percentage return targets.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        adv_entry = get_advanced_trained_models(norm_sym, horizon=horizon, db=db)
        meta = adv_entry["metadata"]

        models_dict = {
            "persistence_baseline": {
                "model_name": "Persistence Baseline (Random Walk)",
                "description": "Predicts future return is zero (P(t+h) = P(t))",
                "test_metrics": meta["baseline_metrics"],
                "is_champion": (meta["champion_model"] == "persistence_baseline")
            },
            "ridge_regression": {
                "model_name": "Ridge Regression (L2 Regularized)",
                "description": "Linear regression with L2 shrinkage and StandardScaler pipeline",
                "test_metrics": meta["ridge_metrics"],
                "is_champion": (meta["champion_model"] == "ridge_regression")
            },
            "random_forest": {
                "model_name": "Random Forest Regressor",
                "description": "Bagging ensemble of 100 decision trees with max depth 5",
                "test_metrics": meta["rf_metrics"],
                "feature_importances": meta["rf_importances"],
                "is_champion": (meta["champion_model"] == "random_forest")
            },
            "xgboost": {
                "model_name": "XGBoost Regressor",
                "description": "Gradient-boosted decision trees with learning rate 0.03",
                "test_metrics": meta["xgb_metrics"],
                "feature_importances": meta["xgb_importances"],
                "is_champion": (meta["champion_model"] == "xgboost")
            },
            "gradient_boosting": {
                "model_name": "HistGradientBoosting Regressor",
                "description": "Histogram-based gradient boosting regressor",
                "test_metrics": meta["gb_metrics"],
                "is_champion": (meta["champion_model"] == "gradient_boosting")
            }
        }

        candidates = list(models_dict.keys())
        best_mae = min(candidates, key=lambda m: models_dict[m]["test_metrics"]["mae"])
        best_da = max(candidates, key=lambda m: models_dict[m]["test_metrics"]["directional_accuracy"])

        return ModelComparisonResponse(
            symbol=norm_sym,
            train_date_range=meta["train_date_range"],
            test_date_range=meta["test_date_range"],
            train_samples=meta["train_samples"],
            test_samples=meta["test_samples"],
            models=models_dict,
            best_model_by_mae=best_mae,
            best_model_by_directional_accuracy=best_da,
            horizon=horizon,
            champion_model=meta["champion_model"],
            champion_rationale=meta["champion_rationale"],
            disclaimer=FINANCIAL_DISCLAIMER
        )
    except InsufficientDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evaluation error for {symbol}: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed for {symbol}: {str(e)}"
        )


@router.post("/train/{symbol}", response_model=ModelComparisonResponse)
def train_symbol_models(
    symbol: str,
    horizon: str = Query("1d", description="Forecast horizon: 1d, 5d, 10d"),
    period: str = Query("2y", description="Historical period for training dataset"),
    db: Session = Depends(get_db)
):
    """
    On-demand model training endpoint. Retrains models, updates serialized artifacts
    and PostgreSQL ML model registry, and returns fresh evaluation metrics.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        adv_entry = train_advanced_models_for_symbol(norm_sym, horizon=horizon, period=period, db=db)
        meta = adv_entry["metadata"]

        models_dict = {
            "persistence_baseline": {
                "model_name": "Persistence Baseline (Random Walk)",
                "description": "Predicts future return is zero",
                "test_metrics": meta["baseline_metrics"],
                "is_champion": (meta["champion_model"] == "persistence_baseline")
            },
            "ridge_regression": {
                "model_name": "Ridge Regression",
                "description": "L2 Regularized linear model with StandardScaler",
                "test_metrics": meta["ridge_metrics"],
                "is_champion": (meta["champion_model"] == "ridge_regression")
            },
            "random_forest": {
                "model_name": "Random Forest Regressor",
                "description": "Bagging ensemble of 100 decision trees",
                "test_metrics": meta["rf_metrics"],
                "feature_importances": meta["rf_importances"],
                "is_champion": (meta["champion_model"] == "random_forest")
            },
            "xgboost": {
                "model_name": "XGBoost Regressor",
                "description": "Gradient-boosted decision trees",
                "test_metrics": meta["xgb_metrics"],
                "feature_importances": meta["xgb_importances"],
                "is_champion": (meta["champion_model"] == "xgboost")
            },
            "gradient_boosting": {
                "model_name": "HistGradientBoosting Regressor",
                "description": "Fast gradient boosted decision trees",
                "test_metrics": meta["gb_metrics"],
                "is_champion": (meta["champion_model"] == "gradient_boosting")
            }
        }

        candidates = list(models_dict.keys())
        best_mae = min(candidates, key=lambda m: models_dict[m]["test_metrics"]["mae"])
        best_da = max(candidates, key=lambda m: models_dict[m]["test_metrics"]["directional_accuracy"])

        return ModelComparisonResponse(
            symbol=norm_sym,
            train_date_range=meta["train_date_range"],
            test_date_range=meta["test_date_range"],
            train_samples=meta["train_samples"],
            test_samples=meta["test_samples"],
            models=models_dict,
            best_model_by_mae=best_mae,
            best_model_by_directional_accuracy=best_da,
            horizon=horizon,
            champion_model=meta["champion_model"],
            champion_rationale=meta["champion_rationale"],
            disclaimer=FINANCIAL_DISCLAIMER
        )
    except InsufficientDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Training error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}"
        )


@router.get("/backtest/{symbol}", response_model=BacktestResultResponse)
def get_backtest_results(
    symbol: str,
    horizon: str = Query("1d", description="Forecast horizon: 1d, 5d, 10d"),
    model_name: str = Query("champion", description="Model name or 'champion'"),
    period: str = Query("2y", description="Historical period for backtesting"),
    db: Session = Depends(get_db)
):
    """
    Executes chronological walk-forward backtest across historical expanding windows.
    Returns walk-forward MAE/RMSE, directional accuracy, error distribution,
    market regime breakdown, and simulated trading equity curve with 0.1% friction.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        res = run_walk_forward_backtest(
            norm_sym,
            horizon=horizon,
            model_name=model_name,
            period=period,
            db=db
        )
        return BacktestResultResponse(
            **res,
            disclaimer=FINANCIAL_DISCLAIMER
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtesting failed for {symbol}: {str(e)}"
        )


@router.get("/drift/{symbol}", response_model=ModelDriftResponse)
def get_drift_status(
    symbol: str,
    model_name: str = Query("champion", description="Model name to audit for concept drift"),
    db: Session = Depends(get_db)
):
    """
    Audits model drift by comparing recent 20-session error against baseline test error.
    Flags drift severity (STABLE, MODERATE_DRIFT, HIGH_DRIFT) and recommends retraining.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        drift_data = check_model_drift(norm_sym, model_name=model_name, db=db)
        return ModelDriftResponse(**drift_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drift evaluation failed for {symbol}: {str(e)}"
        )


@router.get("/prediction-history/{symbol}", response_model=List[PredictionHistoryItem])
def get_symbol_prediction_history(
    symbol: str,
    limit: int = Query(50, description="Max history records to return"),
    db: Session = Depends(get_db)
):
    """
    Returns historical predictions with realized actual closing prices and error telemetry.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        history = get_prediction_history(norm_sym, limit=limit, db=db)
        return [PredictionHistoryItem(**h) for h in history]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch prediction history for {symbol}: {str(e)}"
        )


@router.get("/registry/{symbol}")
def get_model_registry(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    Returns model metadata records logged in PostgreSQL `ml_models` for compliance and auditability.
    """
    norm_sym = normalize_symbol(symbol)
    records = db.query(MLModelRegistry).filter(
        MLModelRegistry.symbol == norm_sym
    ).order_by(MLModelRegistry.trained_at.desc()).limit(20).all()

    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "model_name": r.model_name,
            "model_version": r.model_version,
            "horizon": r.horizon,
            "trained_at": r.trained_at.isoformat(),
            "train_samples": r.train_samples,
            "test_samples": r.test_samples,
            "test_mae": r.test_mae,
            "test_rmse": r.test_rmse,
            "test_directional_accuracy": r.test_directional_accuracy,
            "is_champion": r.is_champion
        }
        for r in records
    ]
