"""Add can_delete to Run table

Revision ID: f6791c2b40d
Revises: 464168cc48ad
Create Date: 2015-11-17 16:22:02.793689

"""

# revision identifiers, used by Alembic.
revision = 'f6791c2b40d'
down_revision = '464168cc48ad'
branch_labels = None
depends_on = None

import sys

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('runs',
      sa.Column('can_delete', sa.Boolean(), nullable=False, server_default=sa.sql.expression.true(), default=True))

def downgrade():
    # downgrade is not supported
    sys.exit(1)
