"""add_item_color

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-07-22 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'j1k2l3m4n5o6'
down_revision: Union[str, None] = 'i0j1k2l3m4n5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SQLAlchemy's Enum(PythonEnumClass) binds each member's uppercase .name
# (not its lowercase .value) as the Postgres enum label by default - see
# e6f7g8h9i0j1_fix_enum_label_casing.py, which had to correct exactly this
# mismatch for two other enums after the fact. Using the uppercase names
# here up front avoids repeating that bug for the new 'color' column.
item_color_enum = postgresql.ENUM(
    'CYAN', 'MAGENTA', 'YELLOW', 'BLACK', 'WHITE', 'OTHER',
    name='itemcolor',
)


def upgrade() -> None:
    item_color_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'items',
        sa.Column('color', item_color_enum, nullable=False, server_default='OTHER'),
    )


def downgrade() -> None:
    op.drop_column('items', 'color')
    item_color_enum.drop(op.get_bind(), checkfirst=True)
