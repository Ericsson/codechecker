"""Extended report data

Revision ID: 40112fd406e3
Revises: 39f9e96071c0
Create Date: 2018-11-15 11:06:36.318406

"""

# revision identifiers, used by Alembic.
revision = '40112fd406e3'
down_revision = '39f9e96071c0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('extended_report_data',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('report_id', sa.Integer(), nullable=False),
                    sa.Column('file_id', sa.Integer(), nullable=True),
                    sa.Column('type', sa.Enum('note',
                                              'macro',
                                              'fixit',
                                              name='extended_data_type'
                                              ), nullable=True),
                    sa.Column('line_begin', sa.Integer(), nullable=True),
                    sa.Column('col_begin', sa.Integer(), nullable=True),
                    sa.Column('line_end', sa.Integer(), nullable=True),
                    sa.Column('col_end', sa.Integer(), nullable=True),
                    sa.Column('message', sa.String(), nullable=True),
                    sa.ForeignKeyConstraint(['file_id'], ['files.id'],
                        name=op.f('fk_extended_report_data_file_id_files'),
                        ondelete='CASCADE',
                        initially='DEFERRED',
                        deferrable=True),
                    sa.ForeignKeyConstraint(['report_id'], ['reports.id'],
                        name=op.f('fk_extended_report_data_report_id_reports'),
                        ondelete='CASCADE',
                        initially='DEFERRED',
                        deferrable=True),
                    sa.PrimaryKeyConstraint('id',
                        name=op.f('pk_extended_report_data')))

    op.create_index(op.f('ix_extended_report_data_file_id'),
                    'extended_report_data', ['file_id'], unique=False)

    op.create_index(op.f('ix_extended_report_data_report_id'),
                    'extended_report_data', ['report_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_report_extended_data_report_id'),
                  table_name='report_extended_data')

    op.drop_index(op.f('ix_report_extended_data_file_id'),
                  table_name='report_extended_data')

    op.drop_table('report_extended_data')
