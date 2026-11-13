"""create_ml_registry_tables

Revision ID: b12e84c59011
Revises: f9c41d72a813
Create Date: 2026-11-13 18:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b12e84c59011'
down_revision: Union[str, None] = 'f9c41d72a813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ml_models
    op.create_table(
        'ml_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False, server_default='v1.0.0'),
        sa.Column('horizon', sa.String(length=16), nullable=False, server_default='1d'),
        sa.Column('training_period', sa.String(length=32), nullable=False, server_default='2y'),
        sa.Column('trained_at', sa.DateTime(), nullable=False),
        sa.Column('features_used', sa.JSON(), nullable=False),
        sa.Column('hyperparameters', sa.JSON(), nullable=True),
        sa.Column('train_samples', sa.Integer(), nullable=False),
        sa.Column('test_samples', sa.Integer(), nullable=False),
        sa.Column('train_date_range', sa.String(length=128), nullable=False),
        sa.Column('test_date_range', sa.String(length=128), nullable=False),
        sa.Column('test_mae', sa.Float(), nullable=False),
        sa.Column('test_rmse', sa.Float(), nullable=False),
        sa.Column('test_mape', sa.Float(), nullable=True),
        sa.Column('test_directional_accuracy', sa.Float(), nullable=False),
        sa.Column('is_champion', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('artifact_path', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ml_models_id'), 'ml_models', ['id'], unique=False)
    op.create_index(op.f('ix_ml_models_symbol'), 'ml_models', ['symbol'], unique=False)
    op.create_index('ix_ml_models_sym_hz_name', 'ml_models', ['symbol', 'horizon', 'model_name'], unique=False)

    # 2. ml_predictions
    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False, server_default='v1.0.0'),
        sa.Column('horizon', sa.String(length=16), nullable=False, server_default='1d'),
        sa.Column('prediction_date', sa.DateTime(), nullable=False),
        sa.Column('target_date', sa.String(length=32), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=False),
        sa.Column('predicted_price', sa.Float(), nullable=False),
        sa.Column('predicted_return_pct', sa.Float(), nullable=False),
        sa.Column('lower_bound', sa.Float(), nullable=False),
        sa.Column('upper_bound', sa.Float(), nullable=False),
        sa.Column('confidence_interval_pct', sa.Float(), nullable=False, server_default='95.0'),
        sa.Column('predicted_direction', sa.String(length=16), nullable=False),
        sa.Column('actual_price', sa.Float(), nullable=True),
        sa.Column('actual_return_pct', sa.Float(), nullable=True),
        sa.Column('absolute_error', sa.Float(), nullable=True),
        sa.Column('direction_matched', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ml_predictions_id'), 'ml_predictions', ['id'], unique=False)
    op.create_index(op.f('ix_ml_predictions_symbol'), 'ml_predictions', ['symbol'], unique=False)
    op.create_index('ix_ml_predictions_sym_date', 'ml_predictions', ['symbol', 'prediction_date'], unique=False)

    # 3. ml_backtests
    op.create_table(
        'ml_backtests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('horizon', sa.String(length=16), nullable=False, server_default='1d'),
        sa.Column('window_type', sa.String(length=32), nullable=False, server_default='expanding'),
        sa.Column('total_steps', sa.Integer(), nullable=False),
        sa.Column('wf_mae', sa.Float(), nullable=False),
        sa.Column('wf_rmse', sa.Float(), nullable=False),
        sa.Column('wf_directional_accuracy', sa.Float(), nullable=False),
        sa.Column('simulated_return_pct', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('regime_metrics', sa.JSON(), nullable=True),
        sa.Column('error_distribution', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ml_backtests_id'), 'ml_backtests', ['id'], unique=False)
    op.create_index(op.f('ix_ml_backtests_symbol'), 'ml_backtests', ['symbol'], unique=False)
    op.create_index('ix_ml_backtests_sym_model', 'ml_backtests', ['symbol', 'model_name', 'horizon'], unique=False)

    # 4. ml_drifts
    op.create_table(
        'ml_drifts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(), nullable=False),
        sa.Column('baseline_mae', sa.Float(), nullable=False),
        sa.Column('recent_mae', sa.Float(), nullable=False),
        sa.Column('drift_ratio', sa.Float(), nullable=False),
        sa.Column('drift_status', sa.String(length=32), nullable=False),
        sa.Column('feature_drift_metrics', sa.JSON(), nullable=True),
        sa.Column('retrain_recommended', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ml_drifts_id'), 'ml_drifts', ['id'], unique=False)
    op.create_index(op.f('ix_ml_drifts_symbol'), 'ml_drifts', ['symbol'], unique=False)
    op.create_index('ix_ml_drifts_sym_model', 'ml_drifts', ['symbol', 'model_name'], unique=False)


def downgrade() -> None:
    op.drop_table('ml_drifts')
    op.drop_table('ml_backtests')
    op.drop_table('ml_predictions')
    op.drop_table('ml_models')

