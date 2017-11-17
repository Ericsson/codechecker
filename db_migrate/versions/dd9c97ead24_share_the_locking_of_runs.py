"""Share the locking of runs across servers via database

Revision ID: dd9c97ead24
Revises: 4b38fa14c27b
Create Date: 2017-11-17 15:44:07.810579

"""

# revision identifiers, used by Alembic.
revision = 'dd9c97ead24'
down_revision = '4b38fa14c27b'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from libcodechecker.server.database.run_db_model import Run


def upgrade():
    op.add_column('runs', sa.Column('lock_timestamp', sa.DateTime(),
                                    nullable=True))


def downgrade():
    op.drop_column('runs', 'lock_timestamp')

    # If there are runs who are in the database with '-2' duration, they
    # must be removed as these rows signify runs which store operation didn't
    # conclude.
    connection = op.get_bind()
    session = Session(bind=connection)
    session.query(Run).filter(Run.duration == -2).delete()
    session.commit()
