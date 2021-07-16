"""Fix setting analysis_info_id_seq

Revision ID: f8291ab1d6be
Revises: a24461972d2e
Create Date: 2021-07-15 16:49:05.354455

"""

# revision identifiers, used by Alembic.
revision = 'f8291ab1d6be'
down_revision = 'a24461972d2e'
branch_labels = None
depends_on = None

from alembic import op


def upgrade():
    ctx = op.get_context()
    dialect = ctx.dialect.name

    if dialect == 'postgresql':
        op.execute("""
            SELECT SETVAL(
                'analysis_info_id_seq',
                (SELECT MAX(id) + 1 FROM analysis_info)
            )
        """)
