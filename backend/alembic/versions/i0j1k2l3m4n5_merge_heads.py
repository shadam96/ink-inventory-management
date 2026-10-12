"""merge_heads

Revision ID: i0j1k2l3m4n5
Revises: f6a7b8c9d0e1, h9i0j1k2l3m4
Create Date: 2026-07-22 08:00:00.000000

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = 'i0j1k2l3m4n5'
down_revision: Union[str, Sequence[str], None] = ('f6a7b8c9d0e1', 'h9i0j1k2l3m4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
