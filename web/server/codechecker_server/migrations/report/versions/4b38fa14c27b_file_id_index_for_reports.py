"""
file_id INDEX for reports

Revision ID: 4b38fa14c27b
Revises:     82ca43f05c10
Create Date: 2017-12-11 09:13:16.301478


Add INDEX for the file_id column in the report table to speed up file cleanup.
"""

from alembic import op


# Revision identifiers, used by Alembic.
revision = '4b38fa14c27b'
down_revision = '82ca43f05c10'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('ix_reports_file_id'), 'reports', ['file_id'],
                    unique=False)


def downgrade():
    op.drop_index(op.f('ix_reports_file_id'), table_name='reports')
