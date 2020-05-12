"""Add description for run history

Revision ID: 5f8a443a51e5
Revises: a79677f54e48
Create Date: 2020-04-09 09:52:52.336709

"""

# revision identifiers, used by Alembic.
revision = '5f8a443a51e5'
down_revision = 'a79677f54e48'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('run_histories',
                  sa.Column('description', sa.String(), nullable=True))


def downgrade():
    op.drop_column('run_histories', 'description')
