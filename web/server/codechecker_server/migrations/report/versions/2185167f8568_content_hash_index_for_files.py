"""content hash index for files

Revision ID: 2185167f8568
Revises: 5f8a443a51e5
Create Date: 2020-07-28 16:02:01.131126

"""

# revision identifiers, used by Alembic.
revision = '2185167f8568'
down_revision = '5f8a443a51e5'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.create_index(op.f('ix_files_content_hash'), 'files', ['content_hash'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_files_content_hash'), table_name='files')
