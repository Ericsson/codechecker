"""file id index for reports

Revision ID: 4b38fa14c27b
Revises: 82ca43f05c10
Create Date: 2017-12-11 09:13:16.301478


Add index for the file ids in the report table to speed up
file cleanup.
"""




# revision identifiers, used by Alembic.
revision = '4b38fa14c27b'
down_revision = '82ca43f05c10'
branch_labels = None
depends_on = None

from alembic import op

def upgrade():
    op.create_index(op.f('ix_reports_file_id'), 'reports', ['file_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_reports_file_id'), table_name='reports')
