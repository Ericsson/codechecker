"""Tag zlib-compressed BLOBs explicitly in the DB

Revision ID: 43384659d572
Revises: 9d956a0fae8d
Create Date: 2024-02-15 16:37:49.828470

"""

# revision identifiers, used by Alembic.
revision = '43384659d572'
down_revision = '9d956a0fae8d'
branch_labels = None
depends_on = None

from logging import getLogger
from typing import Dict, Tuple

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import and_, func, not_
from sqlalchemy.ext.automap import automap_base

from codechecker_common.util import progress


def upgrade():
    # Note: The instantiation of the LOG variable *MUST* stay here so that it
    # uses the facilities that are sourced from the Alembic env.py.
    # Symbols created on the module-level are created *before* Alembic's env.py
    # had loaded.
    LOG = getLogger("migration/report")
    dialect = op.get_context().dialect.name
    conn = op.get_bind()

    LOG.info("Hello")


def downgrade():
    LOG = getLogger("migration/report")
    dialect = op.get_context().dialect.name
    conn = op.get_bind()
