"""
Add index oauth_tokens(auth_session_id)

Revision ID: 635389f535cd
Revises:     511b1b37de2e
Create Date: 2026-08-17 15:28:04.316623
"""

from alembic import op


# Revision identifiers, used by Alembic.
revision = '635389f535cd'
down_revision = '511b1b37de2e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('ix_oauth_tokens_auth_session_id'),
                    'oauth_tokens', ['auth_session_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_oauth_tokens_auth_session_id'),
                  table_name='oauth_tokens')
