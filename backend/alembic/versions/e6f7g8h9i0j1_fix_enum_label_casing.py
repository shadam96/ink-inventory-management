"""Fix enum label casing for userrole.CUSTOMER and movementtype.CONSUMPTION

Prior migrations (c3d4e5f6g7h8, d4e5f6g7h8i9) added the new enum labels in
lowercase ('customer', 'consumption'). SQLAlchemy's `Enum(PythonEnumClass)`
columns in app/models bind the Python member's uppercase `.name` by default
(no `values_callable` is configured anywhere in this codebase), matching the
uppercase labels already used for every other value (ADMIN, MANAGER, RECEIPT,
DISPATCH, ...). As a result, UserRole.CUSTOMER / MovementType.CONSUMPTION
could never actually be persisted - every attempt raised
"invalid input value for enum" at the DB layer. This migration renames the
mismatched labels to the correct casing so the ORM's default binding works.

Revision ID: e6f7g8h9i0j1
Revises: d4e5f6g7h8i9
Create Date: 2026-07-20

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "e6f7g8h9i0j1"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... RENAME VALUE cannot run inside the same transaction as
    # other DDL that references the type; each runs in its own statement.
    op.execute("COMMIT")
    op.execute("ALTER TYPE userrole RENAME VALUE 'customer' TO 'CUSTOMER'")
    op.execute("BEGIN")

    op.execute("COMMIT")
    op.execute("ALTER TYPE movementtype RENAME VALUE 'consumption' TO 'CONSUMPTION'")
    op.execute("BEGIN")


def downgrade() -> None:
    op.execute("COMMIT")
    op.execute("ALTER TYPE userrole RENAME VALUE 'CUSTOMER' TO 'customer'")
    op.execute("BEGIN")

    op.execute("COMMIT")
    op.execute("ALTER TYPE movementtype RENAME VALUE 'CONSUMPTION' TO 'consumption'")
    op.execute("BEGIN")
