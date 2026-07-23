"""normalize_unit_of_measure

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'k2l3m4n5o6p7'
down_revision: Union[str, None] = 'j1k2l3m4n5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The item form used to default unit_of_measure to the UI's *translated*
# placeholder text instead of a fixed value, so an item created while the
# app was set to a non-English language got that language's word for
# "Liter" baked in as real, persisted data - surfacing as mixed-language
# units on the otherwise-English Hand On Stock page. The form default is
# now a fixed empty string (frontend fix), so this backfills the rows that
# already picked up a translated default before that fix.
_LOCALE_LITER_VARIANTS = ['ליטר', 'Λίτρο', 'Litre']


def upgrade() -> None:
    items = sa.table('items', sa.column('unit_of_measure', sa.String))
    op.execute(
        items.update()
        .where(items.c.unit_of_measure.in_(_LOCALE_LITER_VARIANTS))
        .values(unit_of_measure='Liter')
    )


def downgrade() -> None:
    # The original per-row locale text isn't recoverable - nothing to undo.
    pass
