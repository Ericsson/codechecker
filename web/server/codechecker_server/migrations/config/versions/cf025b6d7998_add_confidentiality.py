"""Add confidentiality

Revision ID: cf025b6d7998
Revises: 4db450cf38af
Create Date: 2021-09-08 13:07:08.891285

"""

# revision identifiers, used by Alembic.
revision = 'cf025b6d7998'
down_revision = '4db450cf38af'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('products', sa.Column('confidentiality', sa.String(), nullable=True))


def downgrade():
    op.drop_column('products', 'confidentiality')
