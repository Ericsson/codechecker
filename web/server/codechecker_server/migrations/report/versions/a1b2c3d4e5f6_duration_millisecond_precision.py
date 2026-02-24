"""
Duration millisecond precision

Revision ID: a1b2c3d4e5f6
Revises:     198654dac219
Create Date: 2026-02-24 13:14:00.000000
"""

from alembic import op


revision = 'a1b2c3d4e5f6'
down_revision = '198654dac219'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE runs
        SET duration = duration * 1000
        WHERE duration != -1
    """)


def downgrade():
    op.execute("""
        UPDATE runs
        SET duration = duration / 1000
        WHERE duration != -1
    """)
