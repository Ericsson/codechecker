"""Disable review status change

Revision ID: 3335ff7593cc
Revises: 4964142b58d2
Create Date: 2018-11-29 14:16:58.170551

"""

# revision identifiers, used by Alembic.
revision = '3335ff7593cc'
down_revision = '4964142b58d2'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('products', sa.Column('is_review_status_change_disabled',
                                        sa.Boolean(),
                                        server_default=sa.text(u'false')))


def downgrade():
    op.drop_column('products', 'is_review_status_change_disabled')
