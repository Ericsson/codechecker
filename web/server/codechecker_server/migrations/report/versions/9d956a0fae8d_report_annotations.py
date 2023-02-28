"""Report annotations

Revision ID: 9d956a0fae8d
Revises: 75ae226b5d88
Create Date: 2023-02-09 17:45:56.162040

"""

# revision identifiers, used by Alembic.
revision = '9d956a0fae8d'
down_revision = '75ae226b5d88'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('report_annotations',
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('value', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['report_id'], ['reports.id'], name=op.f('fk_report_annotations_report_id_reports'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('report_id', 'key', name=op.f('pk_report_annotations'))
    )
    op.create_index(op.f('ix_report_annotations_report_id'), 'report_annotations', ['report_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_report_annotations_report_id'), table_name='report_annotations')
    op.drop_table('report_annotations')
