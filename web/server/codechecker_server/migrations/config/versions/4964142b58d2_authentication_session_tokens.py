"""Authentication session tokens

Revision ID: 4964142b58d2
Revises: 6b9f832d0b20
Create Date: 2018-03-28 10:21:38.593302

"""
# revision identifiers, used by Alembic.
revision = '4964142b58d2'
down_revision = '6b9f832d0b20'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('auth_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_name', sa.String(), nullable=True),
        sa.Column('token', sa.CHAR(length=32), nullable=False),
        sa.Column('groups', sa.String(), nullable=True),
        sa.Column('last_access', sa.DateTime(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('can_expire',
                  sa.Boolean(),
                  server_default=sa.text('true'),
                  nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_sessions')),
        sa.UniqueConstraint('token', name=op.f('uq_auth_sessions_token')))
    op.drop_table('user_sessions')


def downgrade():
    op.create_table('user_sessions',
        sa.Column('user_name', sa.VARCHAR(), nullable=False),
        sa.Column('token', sa.CHAR(length=32), nullable=False),
        sa.Column('groups', sa.VARCHAR(), nullable=True),
        sa.Column('last_access', sa.DATETIME(), nullable=False),
        sa.PrimaryKeyConstraint('user_name', name='pk_user_sessions'))
    op.drop_table('auth_sessions')
