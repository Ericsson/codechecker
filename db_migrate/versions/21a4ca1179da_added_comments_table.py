"""Added comments table

Revision ID: 21a4ca1179da
Revises: 30e41fdf2e85
Create Date: 2017-07-20 10:20:53.086556

"""

# revision identifiers, used by Alembic.
revision = '21a4ca1179da'
down_revision = '30e41fdf2e85'
branch_labels = None
depends_on = None

import sys

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('comments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bug_hash', sa.String(), nullable=False),
    sa.Column('author', sa.String(), nullable=False),
    sa.Column('message', sa.Binary(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_comments'))
    )
    op.create_index(op.f('ix_comments_bug_hash'), 'comments', ['bug_hash'], unique=False)

    op.drop_table('reports_to_build_actions')
    op.drop_table('build_actions')


def downgrade():
    # downgrade is not supported
    sys.exit(1)
