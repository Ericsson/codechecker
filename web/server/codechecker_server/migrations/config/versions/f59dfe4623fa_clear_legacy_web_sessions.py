"""
Clear legacy web sessions

Revision ID: f59dfe4623fa
Revises:     00099e8bc212
Create Date: 2025-01-06 22:42:09.589909
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'f59dfe4623fa'
down_revision = '00099e8bc212'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM auth_sessions WHERE can_expire")


def downgrade():
    pass
