"""deduplicate files with same content

Revision ID: 1dd7cd2978aa
Revises: 21a4ca1179da
Create Date: 2017-07-26 13:54:21.400054

"""

# revision identifiers, used by Alembic.
revision = '1dd7cd2978aa'
down_revision = '21a4ca1179da'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from hashlib import sha256
import sys
import zlib


def upgrade():
    content = "dummy content, backward incompatible update"
    hasher = sha256()
    hasher.update(content)
    content_hash = hasher.hexdigest()
    content = zlib.compress(content,
                            zlib.Z_BEST_COMPRESSION)
    content_table = op.create_table('file_contents',
                                    sa.Column('content_hash', sa.String(),
                                              primary_key=True),
                                    sa.Column('content', sa.Binary(),
                                              nullable=False))
    if op.execute(sa.select(['files']).count()) > 0:
        op.bulk_insert(content_table,
                       [{'content_hash': content_hash, 'content': content}])
    op.drop_column('files', 'content')
    op.drop_column('files', 'inc_count')
    op.drop_column('files', 'run_id')
    op.add_column('files',
                  sa.Column('content_hash', sa.String(),
                            sa.ForeignKey('file_contents.content_hash',
                                          deferrable=True,
                                          initially="DEFERRED",
                                          ondelete='CASCADE'),
                            default=content_hash))
    op.create_unique_constraint('uq_files_filepath', 'files',
                                ['filepath', 'content_hash'])


def downgrade():
    # downgrade is not supported
    sys.exit(1)
