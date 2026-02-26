"""add_user_notification_fields

Revision ID: 78d302e07abc
Revises: 84ee75554c1b
Create Date: 2026-02-25 23:45:22.668667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78d302e07abc'
down_revision: Union[str, None] = '84ee75554c1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('notification_email', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_notifications_enabled', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'email_notifications_enabled')
    op.drop_column('users', 'notification_email')


