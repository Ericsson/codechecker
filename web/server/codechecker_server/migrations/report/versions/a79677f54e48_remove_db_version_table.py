"""Remove db version table

Revision ID: a79677f54e48
Revises: 6cb6a3a41967
Create Date: 2020-03-13 12:14:19.805990

"""

# revision identifiers, used by Alembic.
revision = 'a79677f54e48'
down_revision = '6cb6a3a41967'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_table('db_version')


def downgrade():
    op.create_table('db_version',
                    sa.Column('major', sa.INTEGER(), nullable=False),
                    sa.Column('minor', sa.INTEGER(), nullable=False),
                    sa.PrimaryKeyConstraint('major', 'minor',
                                            name='pk_db_version'))
