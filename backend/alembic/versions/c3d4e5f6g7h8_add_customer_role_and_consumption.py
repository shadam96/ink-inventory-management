"""Add CUSTOMER role, customer_id to users, CONSUMPTION movement type

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-04-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction.
    # Commit the current transaction first, then add the enum values.
    op.execute("COMMIT")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'customer'")
    op.execute("ALTER TYPE movementtype ADD VALUE IF NOT EXISTS 'consumption'")

    # Re-open a transaction for the remaining DDL
    op.execute("BEGIN")

    # Add customer_id FK to users table
    op.add_column(
        "users",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_customer_id", "users", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_users_customer_id", table_name="users")
    op.drop_column("users", "customer_id")
    # Note: PostgreSQL does not support removing enum values
