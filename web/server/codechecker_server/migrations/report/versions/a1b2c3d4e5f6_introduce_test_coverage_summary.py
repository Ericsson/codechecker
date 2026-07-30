"""
Introduce test coverage summary table for function coverage

Revision ID: a1b2c3d4e5f6
Revises:     dc2f5efc73a1
Create Date: 2026-04-28 10:00:00.000000
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'dc2f5efc73a1'
branch_labels = None
depends_on = None


def upgrade():
    LOG = getLogger("migration/report")
    op.create_table('test_coverage_summary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=True),
        sa.Column('functions_found', sa.Integer(), default=0,
                  nullable=True),
        sa.Column('functions_hit', sa.Integer(), default=0,
                  nullable=True),
        sa.ForeignKeyConstraint(
            ['file_id'], ['files.id'],
            name=op.f('fk_test_coverage_summary_file_id_files'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True),
        sa.PrimaryKeyConstraint(
            'id', name=op.f('pk_test_coverage_summary'))
    )
    op.create_index(
        op.f('ix_test_coverage_summary_file_id'),
        'test_coverage_summary', ['file_id'], unique=True)


def downgrade():
    LOG = getLogger("migration/report")
    op.drop_index(
        op.f('ix_test_coverage_summary_file_id'),
        table_name='test_coverage_summary')
    op.drop_table('test_coverage_summary')
