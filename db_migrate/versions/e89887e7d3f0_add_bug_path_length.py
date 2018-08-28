"""Add bug path length

Revision ID: e89887e7d3f0
Revises: 3793e361a752
Create Date: 2018-08-28 11:11:07.533906

"""

# revision identifiers, used by Alembic.
revision = 'e89887e7d3f0'
down_revision = '3793e361a752'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():

    op.add_column('reports',
                  sa.Column('path_length', sa.Integer(), nullable=True, default=0))

    conn = op.get_bind()

    conn.execute("""
        UPDATE reports
        SET path_length =
        (SELECT COUNT(bug_path_events.report_id) from bug_path_events where bug_path_events.report_id = reports.id)
    """)


def downgrade():
    op.drop_column('reports', 'path_length')
