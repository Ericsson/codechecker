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
from typing import Any, Callable

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base

from codechecker_common.util import progress

from codechecker_server.database.types import zlib as db_zlib


def _for_each_with_ids(LOG,
                       lower_infinitive: str,
                       lower_gerund: str,
                       upper_gerund: str,
                       db,
                       table_name: str,
                       table_cls,
                       id_field,
                       process_one: Callable[[int, Any], None]):
    id_query = db.query(id_field)
    count = id_query.count()
    if not count:
        return

    def _print_progress(index: int, percent: float):
        LOG.info("[%d/%d] %s '%s'... %.0f%% done.",
                 index, count, upper_gerund, table_name, percent)

    LOG.info("Preparing to %s %d '%s' rows...",
             lower_infinitive, count, table_name)
    for result in progress(id_query.all(), count, 100 // 5,
                           callback=_print_progress):
        id_ = result[0]
        obj = db.query(table_cls).filter(id_field == id_).one()
        process_one(id_, obj)

    db.commit()
    LOG.info("Done %s '%s'.", lower_gerund, table_name)


def upgrade():
    # Upgrade the contents of the existing columns to the new
    # ZLibCompressed format.
    #
    # Note: The underlying ZLibCompressed* types are still represented as
    # LargeBinary in this revision, so the Column type itself needs not be
    # modified, only the content values need migration.
    LOG = getLogger("migration/report")
    dialect = op.get_context().dialect.name
    conn = op.get_bind()
    Base = automap_base()
    Base.prepare(conn, reflect=True)
    db = Session(bind=conn)

    ZLibStr = db_zlib.ZLibCompressedString()

    def _with_ids(table_name: str, table_cls, id_field,
                  process_one: Callable[[int, Any], None]):
        _for_each_with_ids(LOG, "upgrade", "upgrading", "Upgrading",
                           db, table_name, table_cls, id_field, process_one)


def downgrade():
    # Downgrade columns to use raw BLOBs instead of the typed and tagged
    # ZLibCompressed feature. The actual LargeBinary type of the Column needs
    # no modification, only the values.
    LOG = getLogger("migration/report")
    dialect = op.get_context().dialect.name
    conn = op.get_bind()
    Base = automap_base()
    Base.prepare(conn, reflect=True)
    db = Session(bind=conn)

    def _with_ids(table_name: str, table_cls, id_field,
                  process_one: Callable[[int, Any], None]):
        _for_each_with_ids(LOG, "downgrade", "downgrading", "Downgrading",
                           db, table_name, table_cls, id_field, process_one)
