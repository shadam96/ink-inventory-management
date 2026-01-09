"""add_currency_to_items

Revision ID: 4f720e79d8db
Revises: 
Create Date: 2026-01-09 19:31:47.154275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f720e79d8db'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add currency column to items table with default value 'ILS'
    op.add_column('items', sa.Column('currency', sa.String(length=3), nullable=False, server_default='ILS'))


def downgrade() -> None:
    # Remove currency column from items table
    op.drop_column('items', 'currency')


