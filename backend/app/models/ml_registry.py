from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Index
from backend.app.core.database import Base


class MLModelRegistry(Base):
    """Registry of trained models, hyperparams, horizons, and out-of-sample metrics."""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True, nullable=False)
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), default="v1.0.0", nullable=False)
    horizon = Column(String(16), default="1d", nullable=False)  # "1d", "5d", "10d"
    training_period = Column(String(32), default="2y", nullable=False)
    trained_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    features_used = Column(JSON, nullable=False)
    hyperparameters = Column(JSON, nullable=True)
    train_samples = Column(Integer, nullable=False)
    test_samples = Column(Integer, nullable=False)
    train_date_range = Column(String(128), nullable=False)
    test_date_range = Column(String(128), nullable=False)
    test_mae = Column(Float, nullable=False)
    test_rmse = Column(Float, nullable=False)
    test_mape = Column(Float, nullable=True)
    test_directional_accuracy = Column(Float, nullable=False)
    is_champion = Column(Boolean, default=False, nullable=False)
    artifact_path = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ml_models_sym_hz_name", "symbol", "horizon", "model_name"),
    )


class MLPredictionRecord(Base):
    """Historical point and interval predictions with actual outcome realization."""
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True, nullable=False)
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), default="v1.0.0", nullable=False)
    horizon = Column(String(16), default="1d", nullable=False)
    prediction_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    target_date = Column(String(32), nullable=False)
    current_price = Column(Float, nullable=False)
    predicted_price = Column(Float, nullable=False)
    predicted_return_pct = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)
    upper_bound = Column(Float, nullable=False)
    confidence_interval_pct = Column(Float, default=95.0, nullable=False)
    predicted_direction = Column(String(16), nullable=False)  # "UP", "DOWN", "FLAT"
    actual_price = Column(Float, nullable=True)
    actual_return_pct = Column(Float, nullable=True)
    absolute_error = Column(Float, nullable=True)
    direction_matched = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ml_predictions_sym_date", "symbol", "prediction_date"),
    )


class MLBacktestRun(Base):
    """Chronological walk-forward backtest results and regime evaluations."""
    __tablename__ = "ml_backtests"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True, nullable=False)
    model_name = Column(String(64), nullable=False)
    horizon = Column(String(16), default="1d", nullable=False)
    window_type = Column(String(32), default="expanding", nullable=False)
    total_steps = Column(Integer, nullable=False)
    wf_mae = Column(Float, nullable=False)
    wf_rmse = Column(Float, nullable=False)
    wf_directional_accuracy = Column(Float, nullable=False)
    simulated_return_pct = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    regime_metrics = Column(JSON, nullable=True)
    error_distribution = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ml_backtests_sym_model", "symbol", "model_name", "horizon"),
    )


class MLDriftRecord(Base):
    """Model drift monitoring observations and retraining recommendations."""
    __tablename__ = "ml_drifts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True, nullable=False)
    model_name = Column(String(64), nullable=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    baseline_mae = Column(Float, nullable=False)
    recent_mae = Column(Float, nullable=False)
    drift_ratio = Column(Float, nullable=False)
    drift_status = Column(String(32), nullable=False)  # "STABLE", "MODERATE_DRIFT", "HIGH_DRIFT"
    feature_drift_metrics = Column(JSON, nullable=True)
    retrain_recommended = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ml_drifts_sym_model", "symbol", "model_name"),
    )
