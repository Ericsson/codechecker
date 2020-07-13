"""Add analyzer name for report

Revision ID: af5d8a21c1e4
Revises: 2185167f8568
Create Date: 2020-08-14 11:26:01.806877

"""

# revision identifiers, used by Alembic.
revision = 'af5d8a21c1e4'
down_revision = '2185167f8568'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('reports', sa.Column('analyzer_name',
                                       sa.String(),
                                       server_default='unknown',
                                       nullable=False))

def downgrade():
    op.drop_column('reports', 'analyzer_name')
