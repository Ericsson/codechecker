"""Run limitation for products

Revision ID: bb5278995f41
Revises: 150800b30447
Create Date: 2018-03-01 15:38:41.164141

"""
# revision identifiers, used by Alembic.
revision = 'bb5278995f41'
down_revision = '150800b30447'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('products',
                  sa.Column('run_limit', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('products', 'run_limit')
