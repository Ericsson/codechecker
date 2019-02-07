"""New table for server config

Revision ID: dec6feb991e6
Revises: 3335ff7593cc
Create Date: 2019-02-05 17:36:46.527079

"""

# revision identifiers, used by Alembic.
revision = 'dec6feb991e6'
down_revision = '3335ff7593cc'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('server_configurations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('config_key', sa.String(), nullable=False),
    sa.Column('config_value', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_server_configurations'))
    )


def downgrade():
    op.drop_table('server_configurations')
