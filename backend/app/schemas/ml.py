from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

FINANCIAL_DISCLAIMER = (
    "DISCLAIMER: Predictions and indicators provided by StockPulse AI are experimental outputs "
    "for educational and analytical research purposes only. Stock markets are subject to high "
    "volatility and market risk. This system does not constitute investment advice, financial advisory, "
    "or a guarantee of future performance. Never rely solely on automated algorithms for live trading."
)


class ModelMetric(BaseModel):
    mae: float = Field(description="Mean Absolute Error in price units (INR)")
    rmse: float = Field(description="Root Mean Squared Error in price units (INR)")
    directional_accuracy: float = Field(description="Directional Hit Ratio percentage (0-100%)")
    sample_count: int


class ModelEvaluationSummary(BaseModel):
    model_name: str
    description: str
    test_metrics: ModelMetric
    walk_forward_metrics: Optional[ModelMetric] = None
    feature_importances: Optional[Dict[str, float]] = None


class ModelComparisonResponse(BaseModel):
    symbol: str
    train_date_range: str
    test_date_range: str
    train_samples: int
    test_samples: int
    models: Dict[str, Any]
    best_model_by_mae: str
    best_model_by_directional_accuracy: str
    horizon: Optional[str] = "1d"
    champion_model: Optional[str] = None
    champion_rationale: Optional[str] = None
    disclaimer: str = FINANCIAL_DISCLAIMER


class PredictionResult(BaseModel):
    predicted_price: float
    expected_change: float
    expected_change_percent: float
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    model_mae: float
    directional_accuracy_hist: float
    lower_bound_80: Optional[float] = None
    upper_bound_80: Optional[float] = None
    lower_bound_95: Optional[float] = None
    upper_bound_95: Optional[float] = None
    is_champion: Optional[bool] = False


class StockPredictionResponse(BaseModel):
    symbol: str
    current_price: float
    as_of_date: str
    target_date: str
    predictions: Dict[str, Any]
    consensus_predicted_price: float
    consensus_predicted_direction: str
    confidence_level: str  # "LOW", "MODERATE", "HIGH"
    data_source: str
    is_demo: bool = False
    horizon: Optional[str] = "1d"
    champion_model: Optional[str] = None
    champion_predicted_price: Optional[float] = None
    champion_predicted_direction: Optional[str] = None
    champion_predicted_return_pct: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    uncertainty_explanation: Optional[str] = None
    disclaimer: str = FINANCIAL_DISCLAIMER


class ModelInfoResponse(BaseModel):
    architecture: str
    supported_models: List[str]
    features_used: List[str]
    advanced_features_used: Optional[List[str]] = None
    validation_strategy: str
    metrics: List[str]
    data_leakage_safeguards: List[str]
    disclaimer: str = FINANCIAL_DISCLAIMER


# --- Stage 9: Advanced Predictive Intelligence Schemas ---

class AdvancedModelMetrics(BaseModel):
    mae: float = Field(description="Mean Absolute Error in price units (INR)")
    rmse: float = Field(description="Root Mean Squared Error in price units (INR)")
    mape: float = Field(description="Mean Absolute Percentage Error (%)")
    directional_accuracy: float = Field(description="Directional Hit Ratio (0-100%)")
    precision_up: float = Field(description="Precision for UP movements (0-100%)")
    recall_up: float = Field(description="Recall for UP movements (0-100%)")
    f1_up: float = Field(description="F1 Score for UP movements (0-100%)")
    sample_count: int


class ModelEvaluationDetail(BaseModel):
    model_name: str
    display_name: str
    model_type: str
    test_metrics: AdvancedModelMetrics
    walk_forward_metrics: Optional[AdvancedModelMetrics] = None
    is_champion: bool = False
    feature_importances: Optional[Dict[str, float]] = None


class AdvancedModelComparisonResponse(BaseModel):
    symbol: str
    horizon: str
    train_date_range: str
    test_date_range: str
    train_samples: int
    test_samples: int
    models: Dict[str, ModelEvaluationDetail]
    champion_model: str
    champion_rationale: str
    disclaimer: str = FINANCIAL_DISCLAIMER


class MultiHorizonPredictionItem(BaseModel):
    predicted_price: float
    predicted_return_pct: float
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    lower_bound_80: float
    upper_bound_80: float
    lower_bound_95: float
    upper_bound_95: float
    model_mae: float
    directional_accuracy_hist: float
    is_champion: bool = False


class MultiHorizonPredictionResponse(BaseModel):
    symbol: str
    horizon: str  # "1d", "5d", "10d"
    current_price: float
    as_of_date: str
    target_date: str
    predictions: Dict[str, MultiHorizonPredictionItem]
    champion_model: str
    champion_predicted_price: float
    champion_predicted_direction: str
    champion_predicted_return_pct: float
    lower_bound: float
    upper_bound: float
    confidence_level: str  # "LOW", "MODERATE", "HIGH"
    uncertainty_explanation: str
    disclaimer: str = FINANCIAL_DISCLAIMER


class BacktestRegimeMetrics(BaseModel):
    regime: str
    samples: int
    mae: float
    directional_accuracy: float


class BacktestResultResponse(BaseModel):
    symbol: str
    model_name: str
    horizon: str
    total_steps: int
    wf_mae: float
    wf_rmse: float
    wf_directional_accuracy: float
    simulated_return_pct: float
    max_drawdown: float
    win_rate: float
    profit_factor: Optional[float] = None
    regime_breakdown: List[BacktestRegimeMetrics]
    error_distribution: Dict[str, float]
    equity_curve: List[Dict[str, Any]]
    disclaimer: str = FINANCIAL_DISCLAIMER


class ModelDriftResponse(BaseModel):
    symbol: str
    model_name: str
    evaluated_at: str
    baseline_mae: float
    recent_mae: float
    drift_ratio: float
    drift_status: str  # "STABLE", "MODERATE_DRIFT", "HIGH_DRIFT"
    retrain_recommended: bool
    recommendation_text: str
    feature_shifts: Optional[Dict[str, float]] = None


class PredictionHistoryItem(BaseModel):
    id: int
    symbol: str
    model_name: str
    horizon: str
    prediction_date: str
    target_date: str
    current_price: float
    predicted_price: float
    lower_bound: float
    upper_bound: float
    actual_price: Optional[float] = None
    absolute_error: Optional[float] = None
    direction_matched: Optional[bool] = None


