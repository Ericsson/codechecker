"""Add user name and group to session

Revision ID: 6b9f832d0b20
Revises: bb5278995f41
Create Date: 2018-03-13 10:44:38.446589

"""
# revision identifiers, used by Alembic.
revision = '6b9f832d0b20'
down_revision = 'bb5278995f41'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('user_sessions',
        sa.Column('user_name', sa.String(), nullable=False),
        sa.Column('token', sa.CHAR(length=32), nullable=False),
        sa.Column('groups', sa.String(), nullable=True),
        sa.Column('last_access', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('user_name', name=op.f('pk_user_sessions')))
    op.create_index(op.f('ix_user_sessions_token'),
                    'user_sessions', ['token'], unique=False)
    op.drop_table('sessions')


def downgrade():
    op.create_table('sessions',
        sa.Column('auth_string', sa.CHAR(length=64), nullable=False),
        sa.Column('token', sa.CHAR(length=32), nullable=False),
        sa.Column('last_access', sa.DATETIME(), nullable=False),
        sa.PrimaryKeyConstraint('auth_string', name='pk_sessions'))
    op.drop_index(op.f('ix_user_sessions_token'), table_name='user_sessions')
    op.drop_table('user_sessions')
