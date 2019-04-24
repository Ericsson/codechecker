"""Add check command to run history

Revision ID: 080349e895d7
Revises: 101a9cb747de
Create Date: 2018-03-12 15:10:24.652576

"""




# revision identifiers, used by Alembic.
revision = '080349e895d7'
down_revision = '101a9cb747de'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('run_histories',
                  sa.Column('check_command', sa.Binary(), nullable=True))


def downgrade():
    op.drop_column('run_histories', 'check_command')
