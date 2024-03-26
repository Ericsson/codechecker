"""
Store limit

Revision ID: 00099e8bc212
Revises:     7829789fc19c
Create Date: 2023-03-10 16:45:19.301602
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '00099e8bc212'
down_revision = '7829789fc19c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products',
                  sa.Column('report_limit', sa.Integer(),
                            server_default='500000', nullable=False))


def downgrade():
    op.drop_column('products', 'report_limit')
