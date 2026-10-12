"""Make batch_number unique per receipt date instead of globally

The same supplier lot delivered on a later day is a batch of its own, so
batch_number may now repeat across receipt dates.

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-10-10

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "n5o6p7q8r9s0"
down_revision = "m4n5o6p7q8r9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_batches_batch_number", table_name="batches")
    op.create_index("ix_batches_batch_number", "batches", ["batch_number"], unique=False)
    op.create_unique_constraint(
        "uq_batches_batch_number_receipt_date", "batches", ["batch_number", "receipt_date"]
    )


def downgrade() -> None:
    # Fails if a lot was meanwhile received on more than one day.
    op.drop_constraint("uq_batches_batch_number_receipt_date", "batches", type_="unique")
    op.drop_index("ix_batches_batch_number", table_name="batches")
    op.create_index("ix_batches_batch_number", "batches", ["batch_number"], unique=True)
