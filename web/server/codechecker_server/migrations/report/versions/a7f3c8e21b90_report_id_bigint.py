"""
Report id bigint

Revision ID: a7f3c8e21b90
Revises:     24c9660f82b1
Create Date: 2026-06-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'a7f3c8e21b90'
down_revision = '24c9660f82b1'
branch_labels = None
depends_on = None


REPORT_ID_FK_TABLES = [
  ('bug_path_events', False),
  ('bug_report_points', False),
  ('extended_report_data', False),
  ('report_analysis_info', True),
  ('report_annotations', False),
]


def _alter_report_id_columns(type_, existing_type):
    for table, nullable in REPORT_ID_FK_TABLES:
        op.alter_column(
            table,
            'report_id',
            existing_type=existing_type,
            type_=type_,
            existing_nullable=nullable)


def upgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        _alter_report_id_columns(sa.BigInteger(), sa.Integer())
        op.alter_column(
            'reports',
            'id',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
            autoincrement=True)
        op.execute(sa.text('ALTER SEQUENCE reports_id_seq AS BIGINT'))
    elif dialect == 'sqlite':
        # SQLite INTEGER columns already store 64-bit signed integers.
        pass


def downgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        _alter_report_id_columns(sa.Integer(), sa.BigInteger())
        op.alter_column(
            'reports',
            'id',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
            autoincrement=True)
        op.execute(sa.text('ALTER SEQUENCE reports_id_seq AS INTEGER'))
    elif dialect == 'sqlite':
        pass
