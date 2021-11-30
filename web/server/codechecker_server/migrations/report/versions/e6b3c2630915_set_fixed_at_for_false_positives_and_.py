"""Set fixed_at for false positives and intentionals

Revision ID: e6b3c2630915
Revises: fb356f0eefed
Create Date: 2021-12-01 12:01:10.695109

"""

# revision identifiers, used by Alembic.
revision = 'e6b3c2630915'
down_revision = 'fb356f0eefed'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    conn = op.get_bind()

    results = conn.execute("""
        SELECT bug_hash, date
        FROM review_statuses
        WHERE status IN ('false_positive', 'intentional')
    """)

    for row in results:
        conn.execute(f"""
            UPDATE reports
            SET fixed_at = '{row.date}'
            WHERE fixed_at IS NULL AND bug_id = '{row.bug_hash}'
        """)


def downgrade():
    pass
