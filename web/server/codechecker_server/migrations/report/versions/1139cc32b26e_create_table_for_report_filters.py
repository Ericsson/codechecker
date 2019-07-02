"""Create table for report filters

Revision ID: 1139cc32b26e
Revises: 3e91d0612422
Create Date: 2019-07-03 10:17:46.928168

"""

# revision identifiers, used by Alembic.
revision = '1139cc32b26e'
down_revision = '3e91d0612422'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('report_filters',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(), nullable=False),
                    sa.Column('value', sa.String(), nullable=False),
                    sa.Column('username', sa.String(), nullable=True),
                    sa.PrimaryKeyConstraint('id',
                                            name=op.f('pk_report_filters')))


def downgrade():
    op.drop_table('report_filters')
