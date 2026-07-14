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
    'bug_path_events',
    'bug_report_points',
    'extended_report_data',
    'report_analysis_info',
    'report_annotations',
]

ASSOCIATION_TABLES = [
    {
        'name': 'report_analysis_info',
        'pk_name': 'pk_report_analysis_info',
        'columns': ('report_id', 'analysis_info_id'),
    },
    {
        'name': 'run_history_analysis_info',
        'pk_name': 'pk_run_history_analysis_info',
        'columns': ('run_history_id', 'analysis_info_id'),
    },
]


def _alter_report_id_columns_upgrade(type_, existing_type):
    for table in REPORT_ID_FK_TABLES:
        op.alter_column(
            table,
            'report_id',
            existing_type=existing_type,
            type_=type_,
            existing_nullable=(table == 'report_analysis_info'),
            nullable=False)


def _alter_report_id_columns_downgrade(type_, existing_type):
    for table in REPORT_ID_FK_TABLES:
        op.alter_column(
            table,
            'report_id',
            existing_type=existing_type,
            type_=type_,
            existing_nullable=False,
            nullable=(table == 'report_analysis_info'))


def _cleanup_association_tables(dialect):
    for table_info in ASSOCIATION_TABLES:
        table = table_info['name']
        columns = table_info['columns']
        grouped_columns = ', '.join(columns)
        null_condition = " OR ".join(f"{column} IS NULL" for column in columns)

        op.execute(sa.text(
            f"DELETE FROM {table} WHERE {null_condition}"))

        if dialect == 'postgresql':
            op.execute(sa.text(f"""
                WITH to_remove AS MATERIALIZED (
                    SELECT ctid FROM {table}
                    EXCEPT
                    SELECT MIN(ctid) FROM {table} GROUP BY {grouped_columns}
                )
                DELETE FROM {table}
                WHERE ctid IN (
                    SELECT * FROM to_remove
                )
            """))
        else:
            # In old SQLite versions materialized CTEs are not supported.
            op.execute(sa.text(f"""
                DELETE FROM {table}
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM {table}
                    GROUP BY {grouped_columns}
                )
            """))


def _tighten_association_tables_postgresql():
    op.alter_column(
        'run_history_analysis_info',
        'run_history_id',
        existing_type=sa.Integer(),
        nullable=False)
    for table_info in ASSOCIATION_TABLES:
        op.alter_column(
            table_info['name'],
            'analysis_info_id',
            existing_type=sa.Integer(),
            nullable=False)

    op.create_primary_key(
        'pk_report_analysis_info',
        'report_analysis_info',
        ['report_id', 'analysis_info_id'])
    op.create_primary_key(
        'pk_run_history_analysis_info',
        'run_history_analysis_info',
        ['run_history_id', 'analysis_info_id'])


def _tighten_association_tables_sqlite():
    for table_info in ASSOCIATION_TABLES:
        with op.batch_alter_table(table_info['name']) as batch_op:
            for column in table_info['columns']:
                batch_op.alter_column(column, nullable=False)
            batch_op.create_primary_key(
                table_info['pk_name'],
                list(table_info['columns']))


def _relax_association_tables_postgresql():
    op.drop_constraint(
        'pk_run_history_analysis_info',
        'run_history_analysis_info',
        type_='primary')
    op.drop_constraint(
        'pk_report_analysis_info',
        'report_analysis_info',
        type_='primary')

    op.alter_column(
        'run_history_analysis_info',
        'run_history_id',
        existing_type=sa.Integer(),
        nullable=True)
    for table_info in ASSOCIATION_TABLES:
        op.alter_column(
            table_info['name'],
            'analysis_info_id',
            existing_type=sa.Integer(),
            nullable=True)


def _relax_association_tables_sqlite():
    for table_info in ASSOCIATION_TABLES:
        with op.batch_alter_table(table_info['name']) as batch_op:
            batch_op.drop_constraint(table_info['pk_name'], type_='primary')
            for column in table_info['columns']:
                batch_op.alter_column(column, nullable=True)


def upgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    _cleanup_association_tables(dialect)

    if dialect == 'postgresql':
        _alter_report_id_columns_upgrade(sa.BigInteger(), sa.Integer())
        op.alter_column(
            'reports',
            'id',
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
            autoincrement=True)
        op.execute(sa.text('ALTER SEQUENCE reports_id_seq AS BIGINT'))
        _tighten_association_tables_postgresql()
    elif dialect == 'sqlite':
        # SQLite INTEGER columns already store 64-bit signed integers.
        _tighten_association_tables_sqlite()


def downgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        _relax_association_tables_postgresql()
        _alter_report_id_columns_downgrade(sa.Integer(), sa.BigInteger())
        op.alter_column(
            'reports',
            'id',
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
            autoincrement=True)
        op.execute(sa.text('ALTER SEQUENCE reports_id_seq AS INTEGER'))
    elif dialect == 'sqlite':
        _relax_association_tables_sqlite()
