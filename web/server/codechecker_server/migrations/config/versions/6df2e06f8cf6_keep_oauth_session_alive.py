"""
Keep oauth session alive

Revision ID: 6df2e06f8cf6
Revises:     635389f535cd
Create Date: 2026-09-02 23:04:07.756806
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '6df2e06f8cf6'
down_revision = '635389f535cd'
branch_labels = None
depends_on = None


def upgrade():
    LOG = getLogger("migration/config")
    # Nullable: existing rows predate this column and have no provider.
    op.add_column(
        'oauth_tokens',
        sa.Column('provider', sa.String(), nullable=True))


def downgrade():
    LOG = getLogger("migration/config")
    op.drop_column('oauth_tokens', 'provider')
