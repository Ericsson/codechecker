"""Add index for report and history id columns

Revision ID: a24461972d2e
Revises: dabc6998b8f0
Create Date: 2021-06-10 15:38:59.504534

"""

# revision identifiers, used by Alembic.
revision = 'a24461972d2e'
down_revision = 'dabc6998b8f0'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    op.create_index(
        op.f('ix_report_analysis_info_report_id'),
        'report_analysis_info',
        ['report_id'],
        unique=False)

    op.create_index(
        op.f('ix_run_history_analysis_info_run_history_id'),
        'run_history_analysis_info',
        ['run_history_id'],
        unique=False)


def downgrade():
    op.drop_index(
        op.f('ix_run_history_analysis_info_run_history_id'),
        table_name='run_history_analysis_info')

    op.drop_index(
        op.f('ix_report_analysis_info_report_id'),
        table_name='report_analysis_info')
