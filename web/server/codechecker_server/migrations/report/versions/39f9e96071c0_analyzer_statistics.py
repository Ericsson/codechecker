"""Analyzer statistics

Revision ID: 39f9e96071c0
Revises: 9987aa593ca7
Create Date: 2018-09-05 17:45:10.746758

"""

# revision identifiers, used by Alembic.
revision = '39f9e96071c0'
down_revision = '9987aa593ca7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('analyzer_statistics',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('run_history_id', sa.Integer(), nullable=True),
                    sa.Column('analyzer_type', sa.String(), nullable=True),
                    sa.Column('version', sa.Binary(), nullable=True),
                    sa.Column('successful', sa.Integer(), nullable=True),
                    sa.Column('failed', sa.Integer(), nullable=True),
                    sa.Column('failed_files', sa.Binary(), nullable=True),
                    sa.ForeignKeyConstraint(['run_history_id'],
                                            ['run_histories.id'],
                                            name=op.f('fk_analyzer_statistics_run_history_id_run_histories'),
                                            ondelete='CASCADE',
                                            initially='DEFERRED',
                                            deferrable=True),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk_analyzer_statistics'))
                    )
    op.create_index(op.f('ix_analyzer_statistics_run_history_id'),
                    'analyzer_statistics',
                    ['run_history_id'],
                    unique=False)


def downgrade():
    op.drop_index(op.f('ix_analyzer_statistics_run_history_id'),
                  table_name='analyzer_statistics')
    op.drop_table('analyzer_statistics')
