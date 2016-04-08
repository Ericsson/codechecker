"""remove_bug_hash_type

Revision ID: 464168cc48ad
Revises: 2b23d1a4fb96
Create Date: 2015-11-04 17:45:32.136366

"""

# revision identifiers, used by Alembic.
revision = '464168cc48ad'
down_revision = '2b23d1a4fb96'
branch_labels = None
depends_on = None

import sys

from alembic import op


def upgrade():
    """
    remove bug hash type
    """
    op.drop_column('reports', 'bug_id_type')
    op.drop_column('suppress_bug', 'type')


def downgrade():
    """
    downgrade is not supported
    """
    sys.exit(1)
