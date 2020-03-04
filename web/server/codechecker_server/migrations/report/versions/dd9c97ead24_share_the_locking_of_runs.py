"""Share the locking of runs across servers via database

Revision ID: dd9c97ead24
Revises: 4b38fa14c27b
Create Date: 2017-11-17 15:44:07.810579

"""




# revision identifiers, used by Alembic.
revision = 'dd9c97ead24'
down_revision = '4b38fa14c27b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('run_locks',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('locked_at', sa.DateTime(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('name', name=op.f('pk_run_locks'))
    )


def downgrade():
    op.drop_table('run_locks')
