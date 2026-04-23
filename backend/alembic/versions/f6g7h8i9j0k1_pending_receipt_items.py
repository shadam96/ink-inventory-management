"""Create pending_receipt_items table for the shared receive queue

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-04-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6g7h8i9j0k1"
down_revision: Union[str, None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_receipt_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column("manufacturing_date", sa.Date(), nullable=True),
        sa.Column("batch_number", sa.String(length=50), nullable=True),
        sa.Column("supplier_batch_number", sa.String(length=100), nullable=True),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("added_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pending_receipt_items_item_id"),
        "pending_receipt_items",
        ["item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pending_receipt_items_added_by_user_id"),
        "pending_receipt_items",
        ["added_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pending_receipt_items_added_by_user_id"),
        table_name="pending_receipt_items",
    )
    op.drop_index(
        op.f("ix_pending_receipt_items_item_id"),
        table_name="pending_receipt_items",
    )
    op.drop_table("pending_receipt_items")
