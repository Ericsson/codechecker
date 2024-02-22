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

from datetime import datetime
now = datetime.now

import json
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional, cast
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
                      table_class,
                      id_field: str,
                      affected_fields: List[str],
                      transform_one):
    id_column = getattr(table_class, id_field)
    id_query = db.query(id_column)
    count = id_query.count()
    if not count:
        return

    def _print_progress(index: int, percent: float):
        LOG.info("[%d/%d] %s '%s'... %.0f%% done.",
                 index, count, upper_gerund, table_name, percent)

    cols_to_query = [getattr(table_class, col) for col in affected_fields]
    LOG.info("Preparing to %s %d '%s' rows...",
             lower_infinitive, count, table_name)

    start = now()
    all_ids = id_query.all()
    end = now()
    if (end - start).total_seconds() > 1:
        LOG.warning("Head %s(%s): took %s",
                    table_name, id_field, (end - start))

    for result in progress(all_ids, count, 100 // 5,
                           callback=_print_progress):
        id_ = result[0]

        start = now()
        obj = db.query(*cols_to_query) \
            .filter(id_column == id_) \
            .one()
        fields = {col: getattr(obj, col) for col in affected_fields}
        end = now()
        if (end - start).total_seconds() > 1:
            LOG.warning("Load %s(%s = %s): took %s",
                        table_name, id_field, id_, (end - start))

        start = now()
        fields_to_update = transform_one(id_, **fields)
        end = now()
        if (end - start).total_seconds() > 1:
            LOG.warning("Transform %s(%s = %s): took %s",
                        table_name, id_field, id_, (end - start))

        if fields_to_update:
            start = now()
            db.query(table_class) \
                .filter(id_field == id_) \
                .update(fields_to_update,
                        synchronize_session=False)
            end = now()
            if (end - start).total_seconds() > 1:
                LOG.warning("Store %s(%s = %s): took %s",
                            table_name, id_field, id_, (end - start))

    start = now()
    db.commit()
    end = now()
    LOG.info("Done %s '%s'. (COMMIT took %s)", lower_gerund, table_name,
             (end - start))


def upgrade():
    # Upgrade the contents of the existing columns to the new
    # ZLibCompressed format.
    #
    # Note: The underlying ZLibCompressed* types are still represented as
    # LargeBinary in this revision, so the Column type itself needs not be
    # modified, only the content values need migration.
    LOG = getLogger("migration/report")
    conn = op.get_bind()
    Base = automap_base()
    Base.prepare(conn, reflect=True)
    db = Session(bind=conn)

    def with_ids(table_name: str,
                 id_field: str,
                 affected_fields: List[str],
                 transform_one):
        table_class = getattr(Base.classes, table_name)
        for_each_with_ids(LOG, "upgrade", "upgrading", "Upgrading",
                          db, table_name, table_class, id_field,
                          affected_fields, transform_one)

    def upgrade_analysis_info():
        def transform(id_, analyzer_command):
            if analyzer_command is None:
                return {}

            start = now()
            new_analyzer_command = to_z_str(analyzer_command)
            end = now()
            if (end - start).total_seconds() > 1:
                LOG.warning("Migrate '%s'.'%s' (ID = %s): took %s, original *COMPRESSED* size %s, new *COMPRESSED+TAGGED* size %s",
                            "analysis_info", "analyzer_command", id_, (end - start), len(analyzer_command), len(new_analyzer_command))

            ret = {"analyzer_command": new_analyzer_command}
            return ret

        with_ids("analysis_info", "id", ["analyzer_command"], transform)

    def upgrade_analyzer_statistics():
        def transform(id_, version, failed_files):
            ret = {}

            if version is not None:
                start = now()
                new_version = to_z_str(version)
                end = now()
                if (end - start).total_seconds() > 1:
                    LOG.warning("Migrate '%s'.'%s' (ID = %s): took %s, original *COMPRESSED* size %s, new *COMPRESSED+TAGGED* size %s",
                                "analyzer_statistics", "version", id_, (end - start), len(version), len(new_version))

                ret["version"] = new_version
            if failed_files is not None:
                start = now()
                new_failed_files = to_z_str(failed_files)
                end = now()
                if (end - start).total_seconds() > 1:
                    LOG.warning("Migrate '%s'.'%s' (ID = %s): took %s, original *COMPRESSED* size %s, new *COMPRESSED+TAGGED* size %s",
                                "analyzer_statistics", "failed_files", id_, (end - start), len(failed_files), len(new_failed_files))

                ret["failed_files"] = new_failed_files

            return ret

        with_ids("analyzer_statistics", "id", ["version", "failed_files"],
                 transform)

    def upgrade_file_contents():
        def transform(content_hash, content, blame_info):
            start = now()
            new_content = to_z_blob(content)
            end = now()
            if (end - start).total_seconds() > 1:
                LOG.warning("Migrate '%s'.'%s' (contentHash = %s): took %s, original *COMPRESSED* size %s, new *COMPRESSED+TAGGED* size %s",
                            "file_contents", "content", content_hash, (end - start), len(content), len(new_content))

            ret = {"content": new_content}

            if blame_info is not None:
                start = now()
                new_blame_info = migrate_zlib.upgrade_zlib_serialised(
                    blame_info, ZJSON,
                    original_deserialisation_fn=lambda s: json.loads(
                        cast(str, s))
                )
                end = now()
                if (end - start).total_seconds() > 1:
                    LOG.warning("Migrate '%s'.'%s' (contentHash = %s): took %s, original *COMPRESSED* size %s, new *COMPRESSED+TAGGED* size %s",
                                "file_contents", "blame_info", content_hash, (end - start), len(blame_info), len(new_blame_info))

                ret["blame_info"] = new_blame_info

            return ret

        with_ids("file_contents", "content_hash", ["content", "blame_info"],
                 transform)

    upgrade_analysis_info()
    upgrade_analyzer_statistics()
    upgrade_file_contents()


def downgrade():
    # Downgrade columns to use raw BLOBs instead of the typed and tagged
    # ZLibCompressed feature. The actual LargeBinary type of the Column needs
    # no modification, only the values.
    LOG = getLogger("migration/report")
    conn = op.get_bind()
    Base = automap_base()
    Base.prepare(conn, reflect=True)
    db = Session(bind=conn)

    def with_ids(table_name: str,
                 id_field: str,
                 affected_fields: List[str],
                 transform_one):
        table_class = getattr(Base.classes, table_name)
        for_each_with_ids(LOG, "downgrade", "downgrading", "Downgrading",
                          db, table_name, table_class, id_field,
                          affected_fields, transform_one)

    def downgrade_analysis_info():
        def transform(_, analyzer_command):
            if analyzer_command is None:
                return {}
            return {"analyzer_command": to_raw(analyzer_command)}

        with_ids("analysis_info","id", ["analyzer_command"], transform)

    def downgrade_analyzer_statistics():
        def transform(_, version, failed_files):
            ret = {}

            if version is not None:
                ret["version"] = to_raw(version)
            if failed_files is not None:
                ret["failed_files"] = to_raw(failed_files)

            return ret

        with_ids("analyzer_statistics", "id", ["version", "failed_files"],
                 transform)

    def downgrade_file_contents():
        def transform(_, content, blame_info):
            ret = {"content": to_raw(content)}

            if blame_info is not None:
                ret["blame_info"] = \
                    cast(bytes,
                         migrate_zlib.downgrade_zlib_serialised(
                             blame_info, ZJSON,
                             original_serialisation_fn=lambda o:
                             json.dumps(o),
                             compression_level=zlib.Z_BEST_COMPRESSION)
                         )

            return ret

        with_ids("file_contents", "content_hash", ["content", "blame_info"],
                 transform)

    downgrade_analysis_info()
    downgrade_analyzer_statistics()
    downgrade_file_contents()
