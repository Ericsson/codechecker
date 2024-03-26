"""
${message}

Revision ID: ${up_revision}
Revises:     ${down_revision | comma,n}
Create Date: ${create_date}
"""

from logging import getLogger

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}


# Revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    LOG = getLogger("migration/report")
    ${upgrades if upgrades else "pass"}


def downgrade():
    LOG = getLogger("migration/report")
    ${downgrades if downgrades else "pass"}
