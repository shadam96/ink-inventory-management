"""add_barcode_column_to_items

Revision ID: a1b2c3d4e5f6
Revises: 78d302e07abc
Create Date: 2026-03-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '78d302e07abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('barcode', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_items_barcode'), 'items', ['barcode'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_items_barcode'), table_name='items')
    op.drop_column('items', 'barcode')
