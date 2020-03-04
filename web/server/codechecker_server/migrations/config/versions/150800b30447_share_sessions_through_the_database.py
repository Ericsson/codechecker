"""Share sessions through the database

Revision ID: 150800b30447
Revises: 8268fc7ca7f4
Create Date: 2017-11-23 15:26:45.594141

"""
# revision identifiers, used by Alembic.
revision = '150800b30447'
down_revision = '8268fc7ca7f4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('sessions',
    sa.Column('auth_string', sa.CHAR(64), nullable=False),
    sa.Column('token', sa.CHAR(32), nullable=False),
    sa.Column('last_access', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('auth_string',
                            name=op.f('pk_sessions'))
    )


def downgrade():
    op.drop_table('sessions')
