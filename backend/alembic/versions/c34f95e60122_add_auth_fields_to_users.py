"""add_auth_fields_to_users

Revision ID: c34f95e60122
Revises: b12e84c59011
Create Date: 2026-11-13 19:16:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c34f95e60122'
down_revision: Union[str, None] = 'b12e84c59011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add hashed_password and is_superuser to users table
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'hashed_password')
