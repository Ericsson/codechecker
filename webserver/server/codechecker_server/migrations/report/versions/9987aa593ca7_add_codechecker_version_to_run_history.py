"""Add CodeChecker version to run history

Revision ID: 9987aa593ca7
Revises: e89887e7d3f0
Create Date: 2018-09-05 17:43:42.099167

"""

# revision identifiers, used by Alembic.
revision = '9987aa593ca7'
down_revision = 'e89887e7d3f0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('run_histories',
                  sa.Column('cc_version', sa.String(), nullable=True))


def downgrade():
    op.drop_column('run_histories', 'client_version')
