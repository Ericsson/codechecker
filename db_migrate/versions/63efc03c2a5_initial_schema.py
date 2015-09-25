"""Initial schema

Revision ID: 63efc03c2a5
Revises: 
Create Date: 2015-09-25 14:31:57.381866

"""

# revision identifiers, used by Alembic.
revision = '63efc03c2a5'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('db_version',
    sa.Column('major', sa.Integer(), nullable=False),
    sa.Column('minor', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('major', 'minor', name=op.f('pk_db_version'))
    )
    op.create_table('runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('command', sa.String(), nullable=True),
    sa.Column('inc_count', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_runs')),
    sa.UniqueConstraint('name', name=op.f('uq_runs_name'))
    )
    op.create_table('build_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('build_cmd', sa.String(), nullable=True),
    sa.Column('check_cmd', sa.String(), nullable=True),
    sa.Column('failure_txt', sa.String(), nullable=True),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], [u'runs.id'], name=op.f('fk_build_actions_run_id_runs'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_build_actions'))
    )
    op.create_table('configs',
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('checker_name', sa.String(), nullable=False),
    sa.Column('attribute', sa.String(), nullable=False),
    sa.Column('value', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], [u'runs.id'], name=op.f('fk_configs_run_id_runs'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('run_id', 'checker_name', 'attribute', 'value', name=op.f('pk_configs'))
    )
    op.create_table('files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('filepath', sa.String(), nullable=True),
    sa.Column('content', sa.Binary(), nullable=True),
    sa.Column('inc_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], [u'runs.id'], name=op.f('fk_files_run_id_runs'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_files'))
    )
    op.create_table('skip_path',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('path', sa.String(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('comment', sa.Binary(), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], [u'runs.id'], name=op.f('fk_skip_path_run_id_runs'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', 'run_id', name=op.f('pk_skip_path'))
    )
    op.create_table('suppress_bug',
    sa.Column('hash', sa.String(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.Column('comment', sa.Binary(), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], [u'runs.id'], name=op.f('fk_suppress_bug_run_id_runs'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('hash', 'run_id', name=op.f('pk_suppress_bug'))
    )
    op.create_table('bug_path_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('line_begin', sa.Integer(), nullable=True),
    sa.Column('col_begin', sa.Integer(), nullable=True),
    sa.Column('line_end', sa.Integer(), nullable=True),
    sa.Column('col_end', sa.Integer(), nullable=True),
    sa.Column('msg', sa.String(), nullable=True),
    sa.Column('file_id', sa.Integer(), nullable=True),
    sa.Column('next', sa.Integer(), nullable=True),
    sa.Column('prev', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['file_id'], [u'files.id'], name=op.f('fk_bug_path_events_file_id_files'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bug_path_events'))
    )
    op.create_index(op.f('ix_bug_path_events_file_id'), 'bug_path_events', ['file_id'], unique=False)
    op.create_table('bug_report_points',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('line_begin', sa.Integer(), nullable=True),
    sa.Column('col_begin', sa.Integer(), nullable=True),
    sa.Column('line_end', sa.Integer(), nullable=True),
    sa.Column('col_end', sa.Integer(), nullable=True),
    sa.Column('file_id', sa.Integer(), nullable=True),
    sa.Column('next', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['file_id'], [u'files.id'], name=op.f('fk_bug_report_points_file_id_files'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bug_report_points'))
    )
    op.create_index(op.f('ix_bug_report_points_file_id'), 'bug_report_points', ['file_id'], unique=False)
    op.create_table('reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('bug_id', sa.String(), nullable=True),
    sa.Column('bug_id_type', sa.Integer(), nullable=True),
    sa.Column('checker_id', sa.String(), nullable=True),
    sa.Column('checker_cat', sa.String(), nullable=True),
    sa.Column('bug_type', sa.String(), nullable=True),
    sa.Column('severity', sa.Integer(), nullable=True),
    sa.Column('checker_message', sa.String(), nullable=True),
    sa.Column('start_bugpoint', sa.Integer(), nullable=True),
    sa.Column('start_bugevent', sa.Integer(), nullable=True),
    sa.Column('end_bugevent', sa.Integer(), nullable=True),
    sa.Column('suppressed', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['end_bugevent'], [u'bug_path_events.id'], name=op.f('fk_reports_end_bugevent_bug_path_events'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['file_id'], [u'files.id'], name=op.f('fk_reports_file_id_files'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['run_id'], [u'runs.id'], name=op.f('fk_reports_run_id_runs'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['start_bugevent'], [u'bug_path_events.id'], name=op.f('fk_reports_start_bugevent_bug_path_events'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['start_bugpoint'], [u'bug_report_points.id'], name=op.f('fk_reports_start_bugpoint_bug_report_points'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reports'))
    )
    op.create_index(op.f('ix_reports_bug_id'), 'reports', ['bug_id'], unique=False)
    op.create_index(op.f('ix_reports_run_id'), 'reports', ['run_id'], unique=False)
    op.create_table('reports_to_build_actions',
    sa.Column('report_id', sa.Integer(), nullable=False),
    sa.Column('build_action_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['build_action_id'], [u'build_actions.id'], name=op.f('fk_reports_to_build_actions_build_action_id_build_actions'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['report_id'], [u'reports.id'], name=op.f('fk_reports_to_build_actions_report_id_reports'), ondelete=u'CASCADE', initially=u'DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('report_id', 'build_action_id', name=op.f('pk_reports_to_build_actions'))
    )


def downgrade():
    op.drop_table('reports_to_build_actions')
    op.drop_index(op.f('ix_reports_run_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_bug_id'), table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_bug_report_points_file_id'), table_name='bug_report_points')
    op.drop_table('bug_report_points')
    op.drop_index(op.f('ix_bug_path_events_file_id'), table_name='bug_path_events')
    op.drop_table('bug_path_events')
    op.drop_table('suppress_bug')
    op.drop_table('skip_path')
    op.drop_table('files')
    op.drop_table('configs')
    op.drop_table('build_actions')
    op.drop_table('runs')
    op.drop_table('db_version')
