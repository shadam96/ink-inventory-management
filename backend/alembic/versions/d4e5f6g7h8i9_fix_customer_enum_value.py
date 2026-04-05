"""Add missing customer/consumption enum values

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-04-05

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6g7h8i9"
down_revision = "c3d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'customer'")
    op.execute("ALTER TYPE movementtype ADD VALUE IF NOT EXISTS 'consumption'")


def downgrade() -> None:
    pass  # PostgreSQL does not support removing enum values
