"""Remove db version table

Revision ID: 302693c76eb8
Revises: dec6feb991e6
Create Date: 2020-03-13 12:21:07.198231

"""

# revision identifiers, used by Alembic.
revision = '302693c76eb8'
down_revision = 'dec6feb991e6'
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
