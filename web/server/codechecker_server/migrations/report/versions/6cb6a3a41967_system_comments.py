"""System comments

Revision ID: 6cb6a3a41967
Revises: 3e91d0612422
Create Date: 2019-04-02 16:12:46.794131

"""

# revision identifiers, used by Alembic.
revision = '6cb6a3a41967'
down_revision = '3e91d0612422'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('comments', sa.Column('kind',
                                        sa.Integer(),
                                        server_default="0",
                                        nullable=False),)


def downgrade():
    op.drop_column('comments', 'kind')
