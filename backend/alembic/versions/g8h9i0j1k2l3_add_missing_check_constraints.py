"""Add missing CHECK constraints: alerts batch-or-item, batches quantity_received

- alerts.batch_id/item_id were both nullable with nothing enforcing that
  at least one is set, so an orphan alert traceable to nothing could be
  created.
- batches.quantity_received had a non-negative constraint on
  quantity_available but not on quantity_received itself.

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2026-07-21

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "g8h9i0j1k2l3"
down_revision = "f7g8h9i0j1k2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "check_alert_has_batch_or_item",
        "alerts",
        "batch_id IS NOT NULL OR item_id IS NOT NULL",
    )
    op.create_check_constraint(
        "check_quantity_received_non_negative",
        "batches",
        "quantity_received >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("check_quantity_received_non_negative", "batches", type_="check")
    op.drop_constraint("check_alert_has_batch_or_item", "alerts", type_="check")
