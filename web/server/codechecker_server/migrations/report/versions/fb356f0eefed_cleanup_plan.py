"""Cleanup plan

Revision ID: fb356f0eefed
Revises: ad2a567e513a
Create Date: 2021-09-06 10:55:43.093729

"""

# revision identifiers, used by Alembic.
revision = 'fb356f0eefed'
down_revision = 'ad2a567e513a'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('cleanup_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cleanup_plans')),
        sa.UniqueConstraint('name', name=op.f('uq_cleanup_plans_name'))
    )

    op.create_table('cleanup_plan_report_hashes',
        sa.Column('cleanup_plan_id', sa.Integer(), nullable=True),
        sa.Column('bug_hash', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ['cleanup_plan_id'],
            ['cleanup_plans.id'],
            name=op.f('fk_cleanup_plan_report_hashes_cleanup_plan_id_cleanup_plans'),
            ondelete='CASCADE',
            initially='DEFERRED',
            deferrable=True),
        sa.PrimaryKeyConstraint(
            'bug_hash',
            name=op.f('pk_cleanup_plan_report_hashes'))
    )

    op.create_index(
        op.f('ix_cleanup_plan_report_hashes_cleanup_plan_id'),
        'cleanup_plan_report_hashes',
        ['cleanup_plan_id'],
        unique=False)


def downgrade():
    op.drop_index(
        op.f('ix_cleanup_plan_report_hashes_cleanup_plan_id'),
        table_name='cleanup_plan_report_hashes')

    op.drop_table('cleanup_plan_report_hashes')
    op.drop_table('cleanup_plans')
