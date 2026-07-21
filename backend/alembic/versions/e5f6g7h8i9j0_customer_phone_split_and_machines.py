"""Split customer phone into primary/secondary and add customer_machines table

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-04-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Customer phone split ---------------------------------------------
    op.add_column(
        "customers",
        sa.Column("phone_primary", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("phone_secondary", sa.String(length=50), nullable=True),
    )

    # Migrate any existing data from the old single-phone column.
    op.execute("UPDATE customers SET phone_primary = phone WHERE phone IS NOT NULL")

    op.drop_column("customers", "phone")

    # --- Customer machines ------------------------------------------------
    op.create_table(
        "customer_machines",
        sa.Column(
            "customer_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "machine_type",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column("installation_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_machines_customer_id"),
        "customer_machines",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_customer_machines_customer_id"),
        table_name="customer_machines",
    )
    op.drop_table("customer_machines")

    op.add_column(
        "customers",
        sa.Column("phone", sa.String(length=50), nullable=True),
    )
    # Fold primary and secondary back into the single phone column so a
    # rollback during incident response does not silently discard data.
    # COALESCE alone would drop phone_secondary whenever phone_primary is
    # also set; concatenate both when both are present instead so neither
    # value is destroyed (the operator can manually re-split them if the
    # customer_id is later re-upgraded).
    op.execute(
        "UPDATE customers "
        "SET phone = CASE "
        "    WHEN phone_primary IS NOT NULL AND phone_secondary IS NOT NULL "
        "        THEN phone_primary || ' / ' || phone_secondary "
        "    ELSE COALESCE(phone_primary, phone_secondary) "
        "END "
        "WHERE phone_primary IS NOT NULL OR phone_secondary IS NOT NULL"
    )
    op.drop_column("customers", "phone_secondary")
    op.drop_column("customers", "phone_primary")
