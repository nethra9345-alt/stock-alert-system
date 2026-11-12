from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.ml import (
    StockPredictionResponse,
    ModelComparisonResponse,
    ModelEvaluationSummary,
    ModelMetric,
    ModelInfoResponse,
    FINANCIAL_DISCLAIMER
)
from backend.app.ml.engine import (
    predict_next_day,
    get_trained_models,
    train_models_for_symbol
)
from backend.app.ml.features import (
    FEATURE_COLUMNS,
    InsufficientDataError
)
from backend.app.services.market_service import normalize_symbol

router = APIRouter()


@router.get("/models", response_model=ModelInfoResponse)
def get_models_info():
    """Returns architecture overview, feature definitions, and validation methodology."""
    return ModelInfoResponse(
        architecture="Ensemble Quantitative Forecasting System",
        supported_models=[
            "Random Forest Regressor (Non-linear bagging ensemble)",
            "XGBoost Regressor (Gradient-boosted decision trees)",
            "Persistence Baseline (Random walk benchmark: P(t+1) = P(t))"
        ],
        features_used=FEATURE_COLUMNS,
        validation_strategy="Strict Chronological 80/20 Train/Test Split with Expanding TimeSeriesSplit Walk-Forward Validation",
        metrics=[
            "MAE (Mean Absolute Error in INR)",
            "RMSE (Root Mean Squared Error in INR)",
            "Directional Accuracy (% correctly predicted up/down movements)"
        ],
        data_leakage_safeguards=[
            "Zero random shuffling on time series data",
            "Target alignment with strict t+1 forward shift",
            "Features at time t strictly computed using observations <= t",
            "Expanding window out-of-sample walk-forward cross validation",
            "Separation of historical training from forward out-of-sample inference"
        ],
        disclaimer=FINANCIAL_DISCLAIMER
    )


@router.get("/predict/{symbol}", response_model=StockPredictionResponse)
def get_prediction(symbol: str):
    """
    Generates next-day price and directional prediction using pre-trained ML models.
    Reuses serialized models from disk/cache to avoid expensive retraining on every request.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        prediction_data = predict_next_day(norm_sym)
        return StockPredictionResponse(
            **prediction_data,
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
    period: str = Query("2y", description="Historical period for training and evaluation")
):
    """
    Computes rigorous model comparison across Random Forest, XGBoost, and Baseline
    using strict chronological train/test split and walk-forward validation.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        entry = get_trained_models(norm_sym)
        meta = entry["metadata"]

        models_dict = {
            "persistence_baseline": ModelEvaluationSummary(
                model_name="Persistence Baseline (Random Walk)",
                description="Predicts tomorrow's price equals today's closing price (standard econometric benchmark)",
                test_metrics=ModelMetric(**meta["baseline_metrics"])
            ),
            "random_forest": ModelEvaluationSummary(
                model_name="Random Forest Regressor",
                description="Bagging ensemble of 100 decision trees with max depth 6",
                test_metrics=ModelMetric(**meta["rf_metrics"]),
                walk_forward_metrics=ModelMetric(**meta["rf_wf_metrics"]),
                feature_importances=meta["rf_importances"]
            ),
            "xgboost": ModelEvaluationSummary(
                model_name="XGBoost Regressor",
                description="Gradient boosted trees with learning rate 0.05 and feature subsampling",
                test_metrics=ModelMetric(**meta["xgb_metrics"]),
                walk_forward_metrics=ModelMetric(**meta["xgb_wf_metrics"]),
                feature_importances=meta["xgb_importances"]
            )
        }

        # Determine best models
        candidates = ["random_forest", "xgboost", "persistence_baseline"]
        best_mae = min(candidates, key=lambda m: models_dict[m].test_metrics.mae)
        best_da = max(candidates, key=lambda m: models_dict[m].test_metrics.directional_accuracy)

        return ModelComparisonResponse(
            symbol=norm_sym,
            train_date_range=meta["train_date_range"],
            test_date_range=meta["test_date_range"],
            train_samples=meta["train_samples"],
            test_samples=meta["test_samples"],
            models=models_dict,
            best_model_by_mae=best_mae,
            best_model_by_directional_accuracy=best_da,
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
    period: str = Query("2y", description="Historical period for training dataset")
):
    """
    On-demand model training endpoint. Retrains models, updates serialized artifacts,
    and returns fresh evaluation metrics.
    """
    norm_sym = normalize_symbol(symbol)
    try:
        entry = train_models_for_symbol(norm_sym, period=period)
        meta = entry["metadata"]

        models_dict = {
            "persistence_baseline": ModelEvaluationSummary(
                model_name="Persistence Baseline (Random Walk)",
                description="Predicts tomorrow's price equals today's closing price",
                test_metrics=ModelMetric(**meta["baseline_metrics"])
            ),
            "random_forest": ModelEvaluationSummary(
                model_name="Random Forest Regressor",
                description="Bagging ensemble of 100 decision trees",
                test_metrics=ModelMetric(**meta["rf_metrics"]),
                walk_forward_metrics=ModelMetric(**meta["rf_wf_metrics"]),
                feature_importances=meta["rf_importances"]
            ),
            "xgboost": ModelEvaluationSummary(
                model_name="XGBoost Regressor",
                description="Gradient boosted trees with learning rate 0.05",
                test_metrics=ModelMetric(**meta["xgb_metrics"]),
                walk_forward_metrics=ModelMetric(**meta["xgb_wf_metrics"]),
                feature_importances=meta["xgb_importances"]
            )
        }

        candidates = ["random_forest", "xgboost", "persistence_baseline"]
        best_mae = min(candidates, key=lambda m: models_dict[m].test_metrics.mae)
        best_da = max(candidates, key=lambda m: models_dict[m].test_metrics.directional_accuracy)

        return ModelComparisonResponse(
            symbol=norm_sym,
            train_date_range=meta["train_date_range"],
            test_date_range=meta["test_date_range"],
            train_samples=meta["train_samples"],
            test_samples=meta["test_samples"],
            models=models_dict,
            best_model_by_mae=best_mae,
            best_model_by_directional_accuracy=best_da,
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
