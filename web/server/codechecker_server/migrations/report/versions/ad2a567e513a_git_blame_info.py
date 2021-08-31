"""Git blame info

Revision ID: ad2a567e513a
Revises: f8291ab1d6be
Create Date: 2020-12-17 18:08:50.322381

"""

# revision identifiers, used by Alembic.
revision = 'ad2a567e513a'
down_revision = 'f8291ab1d6be'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('files',
                  sa.Column('remote_url', sa.String(), nullable=True))
    op.add_column('files',
                  sa.Column('tracking_branch', sa.String(), nullable=True))

    op.add_column('file_contents',
                  sa.Column('blame_info', sa.Binary(), nullable=True))


def downgrade():
    op.drop_column('file_contents', 'blame_info')
    op.drop_column('files', 'remote_url')
    op.drop_column('files', 'tracking_branch')
