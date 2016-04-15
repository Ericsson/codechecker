"""quick delete

Revision ID: 453083da7cce
Revises: f6791c2b40d
Create Date: 2015-11-26 15:11:36.790627

"""

# revision identifiers, used by Alembic.
revision = '453083da7cce'
down_revision = 'f6791c2b40d'
branch_labels = None
depends_on = None

from alembic import op
import sys

def upgrade():
    op.create_index(op.f('ix_reports_end_bugevent'), 'reports', ['end_bugevent'], unique=False)
    op.create_index(op.f('ix_reports_start_bugevent'), 'reports', ['start_bugevent'], unique=False)


def downgrade():
    sys.exit(-1)
