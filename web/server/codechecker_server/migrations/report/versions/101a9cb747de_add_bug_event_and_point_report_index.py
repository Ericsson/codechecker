"""add bug event and point report index

Revision ID: 101a9cb747de
Revises: dd9c97ead24
Create Date: 2018-02-15 15:30:59.966552

"""




# revision identifiers, used by Alembic.
revision = '101a9cb747de'
down_revision = 'dd9c97ead24'
branch_labels = None
depends_on = None

from alembic import op

def upgrade():
    op.create_index(op.f('ix_bug_path_events_report_id'), 'bug_path_events', ['report_id'], unique=False)
    op.create_index(op.f('ix_bug_report_points_report_id'), 'bug_report_points', ['report_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_bug_path_events_report_id'), table_name='bug_path_events')
    op.drop_index(op.f('ix_bug_report_points_report_id'), table_name='bug_report_points')
