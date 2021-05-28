"""Analysis info table

Revision ID: dabc6998b8f0
Revises: af5d8a21c1e4
Create Date: 2021-05-13 12:05:55.983746

"""

# revision identifiers, used by Alembic.
revision = 'dabc6998b8f0'
down_revision = 'af5d8a21c1e4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()
    ctx = op.get_context()
    dialect = ctx.dialect.name

    analysis_info_tbl = op.create_table('analysis_info',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('analyzer_command', sa.Binary(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_analysis_info'))
    )

    run_history_analysis_info_tbl = op.create_table('run_history_analysis_info',
        sa.Column('run_history_id', sa.Integer(), nullable=True),
        sa.Column('analysis_info_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['analysis_info_id'],
            ['analysis_info.id'],
            name=op.f('fk_run_history_analysis_info_analysis_info_id_analysis_info')),
        sa.ForeignKeyConstraint(
            ['run_history_id'],
            ['run_histories.id'],
            name=op.f('fk_run_history_analysis_info_run_history_id_run_histories'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True)
    )

    report_analysis_info_tbl = op.create_table('report_analysis_info',
        sa.Column('report_id', sa.Integer(), nullable=True),
        sa.Column('analysis_info_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['analysis_info_id'],
            ['analysis_info.id'],
            name=op.f('fk_report_analysis_info_analysis_info_id_analysis_info')),
        sa.ForeignKeyConstraint(
            ['report_id'],
            ['reports.id'],
            name=op.f('fk_report_analysis_info_report_id_reports'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True)
    )

    try:
        run_histories = conn.execute("""
            SELECT id, run_id, check_command
            FROM run_histories
            ORDER BY id DESC
        """).fetchall()

        uniqued_analysis_info = {}
        run_analysis_info = {}
        analysis_info = []
        run_history_analysis_info = []
        for ai_id, (run_history_id, run_id, analyzer_cmd) in enumerate(run_histories, start=1):
            if analyzer_cmd not in uniqued_analysis_info:
                uniqued_analysis_info[analyzer_cmd] = ai_id
                analysis_info.append({
                    'id': ai_id,
                    'analyzer_command': analyzer_cmd
                })

            if run_id not in run_analysis_info:
                run_analysis_info[run_id] = uniqued_analysis_info[analyzer_cmd]

            run_history_analysis_info.append({
                'run_history_id': run_history_id,
                'analysis_info_id': uniqued_analysis_info[analyzer_cmd]
            })

        op.bulk_insert(
            analysis_info_tbl, analysis_info)

        op.bulk_insert(
            run_history_analysis_info_tbl, run_history_analysis_info)
    except:
        print("Analyzer command data migration failed!")
    else:
        # If data migration was successfully finished we can remove the
        # columns.
        if dialect == 'sqlite':
            # Unfortunately removing columns in SQLite is not supported.
            # 'batch_alter_table' function can be used to remove a column here (it
            # will create a new database) but it will clear the table which have
            # foreign keys with cascade delete property. Unfortunately disabling
            # the pragma foreign key doesn't work here. For this reason we will
            # keep these columns in case of SQLite.

            # with op.batch_alter_table('run_histories') as batch_op:
            #     batch_op.drop_column('check_command')

            # with op.batch_alter_table(
            #     'runs',
            #     reflect_args=[
            #         # By default it we don't override the definition of this column
            #         # we will get the following exception:
            #         #   (sqlite3.OperationalError) default value of column
            #         #   [can_delete] is not constant
            #         sa.Column(
            #             'can_delete',
            #             sa.Boolean(),
            #             server_default=sa.sql.true(),
            #             nullable=False
            #         )
            #     ]
            # ) as batch_op:
            #     batch_op.drop_column('command')
            pass
        else:
            op.drop_column('run_histories', 'check_command')
            op.drop_column('runs', 'command')


def downgrade():
    op.add_column('runs',
                  sa.Column('command', sa.VARCHAR(), nullable=True))
    op.add_column('run_histories',
                  sa.Column('check_command', sa.BLOB(), nullable=True))
    op.drop_table('report_analysis_info')
    op.drop_table('run_history_analysis_info')
    op.drop_table('analysis_info')
