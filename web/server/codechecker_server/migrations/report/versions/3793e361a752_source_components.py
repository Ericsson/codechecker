"""Source components

Revision ID: 3793e361a752
Revises: 080349e895d7
Create Date: 2018-04-20 09:29:24.072720

"""




# revision identifiers, used by Alembic.
revision = '3793e361a752'
down_revision = '080349e895d7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('source_components',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('value', sa.Binary(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('name', name=op.f('pk_source_components')))


def downgrade():
    op.drop_table('source_components')
