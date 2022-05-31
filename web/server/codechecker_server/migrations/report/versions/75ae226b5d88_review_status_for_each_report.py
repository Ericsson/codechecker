"""Review status for each report

Revision ID: 75ae226b5d88
Revises: fb356f0eefed
Create Date: 2022-01-27 15:19:48.185835

"""

# revision identifiers, used by Alembic.
revision = '75ae226b5d88'
down_revision = 'fb356f0eefed'
branch_labels = None
depends_on = None

from collections import defaultdict
from alembic import op
import sqlalchemy as sa
import zlib
from io import StringIO

from codechecker_common import util
from codechecker_report_converter.source_code_comment_handler import \
    SourceCodeCommentHandler, SpellException


def upgrade():
    def decode_file_content(content):
        return zlib.decompress(content).decode('utf-8', errors='ignore')

    dialect = op.get_context().dialect.name

    col_rs = sa.Column('review_status', sa.Enum(
        'unreviewed',
        'confirmed',
        'false_positive',
        'intentional',
        name='review_status'), server_default='unreviewed', nullable=True)
    col_rs_author = sa.Column(
        'review_status_author', sa.String(), nullable=True)
    col_rs_date = sa.Column(
        'review_status_date', sa.DateTime(), nullable=True)
    col_rs_is_in_source = sa.Column(
        'review_status_is_in_source',
        sa.Boolean(), server_default='0', nullable=True)
    col_rs_message = sa.Column(
        'review_status_message', sa.Binary(), nullable=True)

    conn = op.get_bind()

    if dialect == 'sqlite':
        op.execute('PRAGMA foreign_keys=off')
        with op.batch_alter_table('reports') as batch_op:
            batch_op.add_column(col_rs)
            batch_op.add_column(col_rs_author)
            batch_op.add_column(col_rs_date)
            batch_op.add_column(col_rs_is_in_source)
            batch_op.add_column(col_rs_message)
        op.execute('PRAGMA foreign_keys=on')

        conn.execute("""
            UPDATE reports
            SET (review_status, review_status_author, review_status_date, review_status_message) =
                (SELECT status, author, date, message FROM review_statuses WHERE bug_hash = reports.bug_id)
        """)
    elif dialect == 'postgresql':
        op.add_column('reports', col_rs)
        op.add_column('reports', col_rs_author)
        op.add_column('reports', col_rs_date)
        op.add_column('reports', col_rs_is_in_source)
        op.add_column('reports', col_rs_message)

        conn.execute("""
            UPDATE reports
            SET review_status = rs.status,
                review_status_author = rs.author,
                review_status_date = rs.date,
                review_status_message = rs.message
            FROM review_statuses AS rs
            WHERE bug_id = rs.bug_hash
        """)

    conn.execute("""
        UPDATE reports
        SET review_status = 'unreviewed'
        WHERE review_status IS NULL
    """)

    files_with_report = conn.execute("""
        SELECT DISTINCT reports.file_id, files.content_hash
        FROM reports INNER JOIN files ON reports.file_id = files.id
        WHERE review_status != 'unreviewed'
    """)

    content_hashes = set()
    hash_to_content = {}
    file_id_to_content_hash = {}

    for f in files_with_report:
        content_hashes.add(f"'{f.content_hash}'")
        file_id_to_content_hash[f.file_id] = f.content_hash

    if content_hashes:
        hash_to_content = conn.execute(f"""
            SELECT content_hash, content FROM file_contents
            WHERE content_hash IN ({','.join(content_hashes)})
        """)

    hash_to_content = {
        x.content_hash: decode_file_content(x.content)
        for x in hash_to_content}

    report_id_to_line = conn.execute(f"""
        SELECT id, file_id, bug_id, checker_id, line FROM reports
        WHERE review_status != 'unreviewed'
    """)

    scch = SourceCodeCommentHandler()
    comment_cache = {}
    bug_hashes = set()
    review_status_in_source = set()
    review_status_to_report_ids = defaultdict(set)

    for row in report_id_to_line:
        cache_key = (file_id_to_content_hash[row.file_id], row.line)
        if cache_key not in comment_cache:
            try:
                comment_cache[cache_key] = scch.get_source_line_comments(
                    StringIO(
                        hash_to_content[file_id_to_content_hash[row.file_id]]),
                    row.line)
            except SpellException:
                comment_cache[cache_key] = []

        for comment in comment_cache[cache_key]:
            if row.checker_id in comment.checkers or \
                    'all' in comment.checkers:
                review_status_in_source.add(row.id)
                bug_hashes.add(f"'{row.bug_id}'")
                review_status_to_report_ids[comment.status].add(row.id)

    if review_status_in_source:
        conn.execute(f"""
            UPDATE reports
            SET review_status_is_in_source = '1'
            WHERE id IN ({','.join(map(str, review_status_in_source))})
        """)

    # Earlier a common review status belonged to all reports sharing the same
    # bug hash even if these reports had different review status given in
    # source code comment. Now these are set individually.
    for review_status, report_ids in review_status_to_report_ids.items():
        conn.execute(f"""
            UPDATE reports
            SET review_status = '{review_status}'
            WHERE id IN ({','.join(map(str, report_ids))})
        """)

    results = conn.execute("""
        SELECT bug_hash, date
        FROM review_statuses
        WHERE status IN ('false_positive', 'intentional')
    """)

    for row in results:
        if dialect == 'sqlite':
            conn.execute(f"""
                UPDATE reports
                SET fixed_at = max('{row.date}', detected_at)
                WHERE fixed_at IS NULL AND bug_id = '{row.bug_hash}'
            """)
        elif dialect == 'postgresql':
            conn.execute(f"""
                UPDATE reports
                SET fixed_at = greatest('{row.date}', detected_at)::timestamp
                WHERE fixed_at IS NULL AND bug_id = '{row.bug_hash}'
            """)

    if bug_hashes:
        conn.execute(f"""
            DELETE FROM review_statuses
            WHERE bug_hash IN ({','.join(bug_hashes)})
        """)


def downgrade():
    op.drop_column('reports', 'review_status_message')
    op.drop_column('reports', 'review_status_is_in_source')
    op.drop_column('reports', 'review_status_date')
    op.drop_column('reports', 'review_status_author')
    op.drop_column('reports', 'review_status')
