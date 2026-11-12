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
    models: Dict[str, ModelEvaluationSummary]
    best_model_by_mae: str
    best_model_by_directional_accuracy: str
    disclaimer: str = FINANCIAL_DISCLAIMER


class PredictionResult(BaseModel):
    predicted_price: float
    expected_change: float
    expected_change_percent: float
    predicted_direction: str  # "UP", "DOWN", "FLAT"
    model_mae: float
    directional_accuracy_hist: float


class StockPredictionResponse(BaseModel):
    symbol: str
    current_price: float
    as_of_date: str
    target_date: str
    predictions: Dict[str, PredictionResult]
    consensus_predicted_price: float
    consensus_predicted_direction: str
    confidence_level: str  # "LOW", "MODERATE", "HIGH"
    data_source: str
    is_demo: bool = False
    disclaimer: str = FINANCIAL_DISCLAIMER


class ModelInfoResponse(BaseModel):
    architecture: str
    supported_models: List[str]
    features_used: List[str]
    validation_strategy: str
    metrics: List[str]
    data_leakage_safeguards: List[str]
    disclaimer: str = FINANCIAL_DISCLAIMER

