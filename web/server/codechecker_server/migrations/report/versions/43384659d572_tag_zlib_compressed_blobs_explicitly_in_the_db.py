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

import json
from logging import getLogger
from typing import Any, Callable
import zlib

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base

from codechecker_common.util import progress

from codechecker_server.database.types import zlib as db_zlib
from codechecker_server.migrations.type_support import zlib as migrate_zlib


ZBlob = db_zlib.ZLibCompressedBlob()
ZStr = db_zlib.ZLibCompressedString()
ZJSON = db_zlib.ZLibCompressedJSON()


def to_z_blob(compressed_value: bytes) -> bytes:
    return migrate_zlib.upgrade_zlib_raw_to_tagged(compressed_value, ZBlob)


def to_z_str(compressed_value: bytes) -> bytes:
    return migrate_zlib.upgrade_zlib_raw_to_tagged(compressed_value, ZStr)


def to_raw(tagged_value: bytes) -> bytes:
    return migrate_zlib.downgrade_zlib_tagged_to_raw(tagged_value)


def for_each_with_ids(LOG,
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

    def with_ids(table_name: str, table_cls, id_field,
                 process_one: Callable[[int, Any], None]):
        for_each_with_ids(LOG, "upgrade", "upgrading", "Upgrading",
                          db, table_name, table_cls, id_field, process_one)

    def upgrade_analysis_info():
        AnalysisInfo = Base.classes.analysis_info

        def process(_, analysis_info):
            if analysis_info.analyzer_command is None:
                return
            analysis_info.analyzer_command = to_z_str(
                analysis_info.analyzer_command)
            db.flush()

        with_ids("analysis_info", AnalysisInfo, AnalysisInfo.id, process)

    def upgrade_analyzer_statistics():
        AnalyzerStatistic = Base.classes.analyzer_statistics

        def process(_, analyzer_statistic):
            if analyzer_statistic.version is not None:
                analyzer_statistic.version = to_z_str(
                    analyzer_statistic.version)
            if analyzer_statistic.failed_files is not None:
                analyzer_statistic.failed_files = to_z_str(
                    analyzer_statistic.failed_files)

            if analyzer_statistic in db.dirty:
                db.flush()

        with_ids("analyzer_statistics", AnalyzerStatistic,
                 AnalyzerStatistic.id, process)

    def upgrade_file_contents():
        FileContent = Base.classes.file_contents

        def process(_, file_content):
            file_content.content = to_z_blob(file_content.content)
            if file_content.blame_info is not None:
                file_content.blame_info = \
                    migrate_zlib.upgrade_zlib_serialised(
                        file_content.blame_info, ZJSON,
                        original_deserialisation_fn=lambda s: json.loads(s))
            db.flush()

        with_ids("file_contents", FileContent, FileContent.content_hash,
                 process)

    upgrade_analysis_info()
    upgrade_analyzer_statistics()
    upgrade_file_contents()


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

    def with_ids(table_name: str, table_cls, id_field,
                 process_one: Callable[[int, Any], None]):
        for_each_with_ids(LOG, "downgrade", "downgrading", "Downgrading",
                          db, table_name, table_cls, id_field, process_one)

    def downgrade_analysis_info():
        AnalysisInfo = Base.classes.analysis_info

        def process(_, analysis_info):
            if analysis_info.analyzer_command is None:
                return
            analysis_info.analyzer_command = to_raw(
                analysis_info.analyzer_command)
            db.flush()

        with_ids("analysis_info", AnalysisInfo, AnalysisInfo.id, process)

    def downgrade_analyzer_statistics():
        AnalyzerStatistic = Base.classes.analyzer_statistics

        def process(_, analyzer_statistic):
            if analyzer_statistic.version is not None:
                analyzer_statistic.version = to_raw(
                    analyzer_statistic.version)
            if analyzer_statistic.failed_files is not None:
                analyzer_statistic.failed_files = to_raw(
                    analyzer_statistic.failed_files)

            if analyzer_statistic in db.dirty:
                db.flush()

        with_ids("analyzer_statistics", AnalyzerStatistic,
                 AnalyzerStatistic.id, process)

    def downgrade_file_contents():
        FileContent = Base.classes.file_contents

        def process(_, file_content):
            file_content.content = to_raw(file_content.content)
            if file_content.blame_info:
                file_content.blame_info = \
                    migrate_zlib.downgrade_zlib_serialised(
                        file_content.blame_info, ZJSON,
                        original_serialisation_fn=lambda o: json.dumps(o),
                        compression_level=zlib.Z_BEST_COMPRESSION)
            db.flush()

        with_ids("file_contents", FileContent, FileContent.content_hash,
                 process)

    downgrade_analysis_info()
    downgrade_analyzer_statistics()
    downgrade_file_contents()
