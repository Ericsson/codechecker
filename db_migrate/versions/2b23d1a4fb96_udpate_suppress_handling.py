"""udpate suppress handling

Revision ID: 2b23d1a4fb96
Revises: 63efc03c2a5
Create Date: 2015-10-06 12:40:06.669407

"""

# revision identifiers, used by Alembic.
revision = '2b23d1a4fb96'
down_revision = '63efc03c2a5'
branch_labels = None
depends_on = None

import sys

from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence

# NOTICE!
# kept here only for later reference if required for other
# db upgrades if full table copy or data modification is required
#
# helper table
#suppress_bug_helper = sa.Table(
#    'suppress_bug',
#    sa.MetaData(),
#    sa.Column('file_name', sa.String()),
#    sa.Column('hash', sa.String()),
#)
# NOTICE END

def upgrade():

    op.drop_constraint('pk_suppress_bug', 'suppress_bug', type_='primary')
    op.add_column('suppress_bug',
                  sa.Column('file_name', sa.String(), nullable=True))
    # add new id primary key
    op.add_column('suppress_bug',
                  sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True))

    # create constraint
    op.create_primary_key(
                "pk_suppress_bug", "suppress_bug",
                ["id"]
            )

    # required to fill up autoincrement values for the id
    op.execute(CreateSequence(Sequence('suppress_bug_id')))
    op.alter_column("suppress_bug",
                    "id",
                    nullable=False,
                    server_default=sa.text("nextval('suppress_bug_id'::regclass)"))


    # NOTICE!
    # kept here only for later reference if required for other
    # db upgrades if full table copy or data modification is required
    # copy the full table and during the copy modify values if required
    # use the current connection
    #connection = op.get_bind()

    #for sp_bug in connection.execute(suppress_bug_helper.select()):
    #    connection.execute(
    #        suppress_bug_helper.update().where(
    #            suppress_bug_helper.c.hash == sp_bug.hash
    #        ).values(
    #            file_name='',
    #        )
    #    )
    # NOTICE END

def downgrade():
    # downgrade is not supported
    sys.exit(1)
