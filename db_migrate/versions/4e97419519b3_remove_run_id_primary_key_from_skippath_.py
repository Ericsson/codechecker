"""Remove run_id primary key from SkipPath table

Revision ID: 4e97419519b3
Revises: 453083da7cce
Create Date: 2016-02-12 13:34:23.302931

"""

# revision identifiers, used by Alembic.
revision = '4e97419519b3'
down_revision = '453083da7cce'
branch_labels = None
depends_on = None

import sys
from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    remove primary key constraint for run_id in the skip path table
    """
    op.drop_constraint('pk_skip_path', 'skip_path', type_='primary')

    # create new primary key constraint for the id only
    op.create_primary_key(
                "pk_skip_path", "skip_path",
                ["id"]
            )

    op.alter_column('skip_path',
                  sa.Column('run_id', sa.Integer(), nullable=False))

def downgrade():
    # downgrade is not supported
    sys.exit(1)
