"""add_system_settings

Revision ID: f6a7b8c9d0e1
Revises: e5f6g7h8i9j0
Create Date: 2026-05-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usd_to_ils', sa.Numeric(12, 4), server_default='3.7', nullable=False),
        sa.Column('eur_to_ils', sa.Numeric(12, 4), server_default='4.0', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # Seed the singleton row.
    op.execute(
        "INSERT INTO system_settings (id, usd_to_ils, eur_to_ils) VALUES (1, 3.7, 4.0)"
    )


def downgrade() -> None:
    op.drop_table('system_settings')
