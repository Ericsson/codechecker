"""
Initial schema

Revision ID: 82ca43f05c10
Revises:     <None>
Create Date: 2017-09-18 21:00:11.593693
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = '82ca43f05c10'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bug_hash', sa.String(), nullable=False),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('message', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_comments'))
    )
    op.create_index(op.f('ix_comments_bug_hash'), 'comments', ['bug_hash'],
                    unique=False)

    op.create_table(
        'db_version',
        sa.Column('major', sa.Integer(), nullable=False),
        sa.Column('minor', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('major', 'minor', name=op.f('pk_db_version'))
    )

    op.create_table(
        'file_contents',
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=True),
        sa.PrimaryKeyConstraint('content_hash', name=op.f('pk_file_contents'))
    )

    op.create_table(
        'review_statuses',
        sa.Column('bug_hash', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('unreviewed',
                                    'confirmed',
                                    'false_positive',
                                    'intentional',
                                    name='review_status'),
                  nullable=False),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('message', sa.LargeBinary(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('bug_hash', name=op.f('pk_review_statuses'))
    )

    op.create_table(
        'runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('command', sa.String(), nullable=True),
        sa.Column('can_delete', sa.Boolean(), server_default=sa.text('true'),
                  nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_runs')),
        sa.UniqueConstraint('name', name=op.f('uq_runs_name'))
    )

    op.create_table(
        'files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filepath', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['content_hash'],
                                ['file_contents.content_hash'],
                                name=op.f(
                                    'fk_files_content_hash_file_contents'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_files')),
        sa.UniqueConstraint('filepath', 'content_hash',
                            name=op.f('uq_files_filepath'))
    )

    op.create_table(
        'run_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('version_tag', sa.String(), nullable=True),
        sa.Column('user', sa.String(), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'],
                                name=op.f('fk_run_histories_run_id_runs'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_run_histories')),
        sa.UniqueConstraint('run_id', 'version_tag',
                            name=op.f('uq_run_histories_run_id'))
    )
    op.create_index(op.f('ix_run_histories_run_id'), 'run_histories',
                    ['run_id'], unique=False)

    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=True),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('bug_id', sa.String(), nullable=True),
        sa.Column('checker_id', sa.String(), nullable=True),
        sa.Column('checker_cat', sa.String(), nullable=True),
        sa.Column('bug_type', sa.String(), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=True),
        sa.Column('line', sa.Integer(), nullable=True),
        sa.Column('column', sa.Integer(), nullable=True),
        sa.Column('checker_message', sa.String(), nullable=True),
        sa.Column('detection_status', sa.Enum('new',
                                              'unresolved',
                                              'resolved',
                                              'reopened',
                                              name='detection_status'),
                  nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('fixed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'],
                                name=op.f('fk_reports_file_id_files'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'],
                                name=op.f('fk_reports_run_id_runs'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_reports'))
    )
    op.create_index(op.f('ix_reports_bug_id'), 'reports', ['bug_id'],
                    unique=False)
    op.create_index(op.f('ix_reports_run_id'), 'reports', ['run_id'],
                    unique=False)

    op.create_table(
        'bug_path_events',
        sa.Column('line_begin', sa.Integer(), nullable=True),
        sa.Column('col_begin', sa.Integer(), nullable=True),
        sa.Column('line_end', sa.Integer(), nullable=True),
        sa.Column('col_end', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('msg', sa.String(), nullable=True),
        sa.Column('file_id', sa.Integer(), nullable=True),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'],
                                name=op.f('fk_bug_path_events_file_id_files'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'],
                                name=op.f(
                                    'fk_bug_path_events_report_id_reports'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.PrimaryKeyConstraint('order', 'report_id',
                                name=op.f('pk_bug_path_events'))
    )
    op.create_index(op.f('ix_bug_path_events_file_id'), 'bug_path_events',
                    ['file_id'], unique=False)

    op.create_table(
        'bug_report_points',
        sa.Column('line_begin', sa.Integer(), nullable=True),
        sa.Column('col_begin', sa.Integer(), nullable=True),
        sa.Column('line_end', sa.Integer(), nullable=True),
        sa.Column('col_end', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=True),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'],
                                name=op.f(
                                    'fk_bug_report_points_file_id_files'),
                                ondelete='CASCADE', initially='DEFERRED',
                                deferrable=True),
        sa.ForeignKeyConstraint(
            ['report_id'], ['reports.id'],
            name=op.f('fk_bug_report_points_report_id_reports'),
            ondelete='CASCADE', initially='DEFERRED', deferrable=True),
        sa.PrimaryKeyConstraint('order', 'report_id',
                                name=op.f('pk_bug_report_points'))
    )
    op.create_index(op.f('ix_bug_report_points_file_id'), 'bug_report_points',
                    ['file_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_bug_report_points_file_id'),
                  table_name='bug_report_points')
    op.drop_table('bug_report_points')
    op.drop_index(op.f('ix_bug_path_events_file_id'),
                  table_name='bug_path_events')
    op.drop_table('bug_path_events')
    op.drop_index(op.f('ix_reports_run_id'),
                  table_name='reports')
    op.drop_index(op.f('ix_reports_bug_id'),
                  table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_run_histories_run_id'),
                  table_name='run_histories')
    op.drop_table('run_histories')
    op.drop_table('files')
    op.drop_table('runs')
    op.drop_table('review_statuses')
    op.drop_table('file_contents')
    op.drop_table('db_version')
    op.drop_index(op.f('ix_comments_bug_hash'), table_name='comments')
    op.drop_table('comments')
