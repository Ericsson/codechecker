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

from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence


def upgrade():
    op.drop_constraint('pk_suppress_bug', 'suppress_bug', type_='primary')
    op.add_column('suppress_bug',
                  sa.Column('file_name', sa.String(), nullable=True))
    # add new id primary key
    op.add_column('suppress_bug',
                  sa.Column('id', sa.Integer(), primary_key=True))
    ## required to fill up autoincrement values for the id
    op.execute(CreateSequence(Sequence('suppress_bug_id')))
    op.alter_column("suppress_bug",
                    "id",
                    nullable=False,
                    server_default=sa.text("nextval('suppress_bug_id'::regclass)"))


def downgrade():
    # downgrade is not supported
    pass
