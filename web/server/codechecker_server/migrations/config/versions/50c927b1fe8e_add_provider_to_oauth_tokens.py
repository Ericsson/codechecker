"""
add provider to oauth tokens

Revision ID: 50c927b1fe8e
Revises:     635389f535cd
Create Date: 2026-08-25 10:13:54.743146
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa



# Revision identifiers, used by Alembic.
revision = '50c927b1fe8e'
down_revision = '635389f535cd'
branch_labels = None
depends_on = None


def upgrade():
    LOG = getLogger("migration/config")
    # Existing rows predate this column and have no known provider, so
    # leave it nullable for them -- the server treats a NULL provider as
    # "not silently refreshable" and falls back to a normal re-login.
    op.add_column(
        'oauth_tokens',
        sa.Column('provider', sa.String(), nullable=True))


def downgrade():
    LOG = getLogger("migration/config")
    op.drop_column('oauth_tokens', 'provider')
