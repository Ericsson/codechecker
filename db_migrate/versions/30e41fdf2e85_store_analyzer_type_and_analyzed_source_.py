"""Store analyzer type and analyzed source file to the database for each buildaction

Revision ID: 30e41fdf2e85
Revises: 4e97419519b3
Create Date: 2016-07-04 15:36:26.208047

"""

# revision identifiers, used by Alembic.
revision = '30e41fdf2e85'
down_revision = '4e97419519b3'
branch_labels = None
depends_on = None

import sys

from alembic import op
import sqlalchemy as sa


def upgrade():
    '''
    extend build_actions table with columns to identify if
    the results for a build_action should be deleted in update mode

    analyzer_type: is required to identify the analyzer which analyzer analyzed the build action

    analyzed_source_file: is required to identify which source file was analyzed in the build action (it is possible to contain multiple source files)
    '''

    op.add_column('build_actions',
                  sa.Column('analyzed_source_file',
                            sa.String(),
                            nullable=False,
                            server_default='')
                  )

    op.add_column('build_actions',
                  sa.Column('analyzer_type',
                            sa.String(),
                            nullable=False,
                            server_default='')
                  )


def downgrade():
    # downgrade is not supported
    sys.exit(1)
