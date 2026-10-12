"""Add batches.scrapped_at

Scrapping keeps quantity_available and records no movement, so the
dashboard's write-off and inventory history need to know when it happened.
Existing scrapped batches are backfilled from updated_at, the best record
there is of when they were scrapped.

Revision ID: o6p7q8r9s0t1
Revises: n5o6p7q8r9s0
Create Date: 2026-10-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "o6p7q8r9s0t1"
down_revision = "n5o6p7q8r9s0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("batches", sa.Column("scrapped_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE batches SET scrapped_at = updated_at WHERE status = 'SCRAP'")


def downgrade() -> None:
    op.drop_column("batches", "scrapped_at")
