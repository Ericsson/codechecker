"""
Add test coverage table

Revision ID: 40eee4fd9122
Revises:     feb5f01b5b52
Create Date: 2026-10-01 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '40eee4fd9122'
down_revision = 'feb5f01b5b52'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'test_coverage',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('lines_found', sa.Integer(), nullable=False),
        sa.Column('lines_hit', sa.Integer(), nullable=False),
        sa.Column('functions_found', sa.Integer(), nullable=False),
        sa.Column('functions_hit', sa.Integer(), nullable=False),
        sa.Column('covered_lines', sa.LargeBinary(), nullable=False),
        sa.Column('uncovered_lines', sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ['run_id'], ['runs.id'],
            name=op.f('fk_test_coverage_run_id_runs'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True),
        sa.ForeignKeyConstraint(
            ['file_id'], ['files.id'],
            name=op.f('fk_test_coverage_file_id_files'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_test_coverage')),
        sa.UniqueConstraint(
            'run_id', 'file_id', name=op.f('uq_test_coverage_run_id'))
    )
    op.create_index(
        op.f('ix_test_coverage_file_id'),
        'test_coverage', ['file_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_test_coverage_file_id'),
                  table_name='test_coverage')
    op.drop_table('test_coverage')
