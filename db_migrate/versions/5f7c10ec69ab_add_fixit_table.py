"""Add fixit table

Revision ID: 5f7c10ec69ab
Revises: 101a9cb747de
Create Date: 2018-03-29 16:19:43.524632

"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

# revision identifiers, used by Alembic.
revision = '5f7c10ec69ab'
down_revision = '101a9cb747de'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('fixits',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('line', sa.Integer(), nullable=False),
                    sa.Column('column', sa.Integer(), nullable=False),
                    sa.Column('message', sa.String(), nullable=False),
                    sa.Column('file_id', sa.Integer(), nullable=True),
                    sa.Column('report_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['file_id'], [u'files.id'], name=op.f(
                            'fk_fixits_file_id_files'), ondelete=u'CASCADE',
                        initially=u'DEFERRED', deferrable=True),
                    sa.ForeignKeyConstraint(
                        ['report_id'], [u'reports.id'], name=op.f(
                            'fk_fixits_report_id_reports'), ondelete=u'CASCADE',
                        initially=u'DEFERRED', deferrable=True),
                    sa.PrimaryKeyConstraint(
                        'id', 'report_id', name=op.f('pk_fixits')))
    op.create_index(op.f('ix_fixits_file_id'),
                    'fixits', ['file_id'], unique=False)
    op.create_index(op.f('ix_fixits_report_id'),
                    'fixits', ['report_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_fixits_report_id'), table_name='fixits')
    op.drop_index(op.f('ix_fixits_file_id'), table_name='fixits')
    op.drop_table('fixits')
