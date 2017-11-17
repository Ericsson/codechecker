# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Perform automatic cleanup routines on the database.
"""

from datetime import datetime, timedelta

from codeCheckerDBAccess_v6.ttypes import *

from libcodechecker.logger import get_logger
from libcodechecker.server.database.run_db_model import *

LOG = get_logger('server')


def remove_stale_runs(session):
    LOG.debug("Pruning of stale runs whose storage went away started...")

    locks_expired_at = datetime.now() - timedelta(minutes=30)

    session.query(Run) \
        .filter(and_(Run.duration == -2,
                     Run.lock_timestamp < locks_expired_at)) \
        .delete(synchronize_session=False)

    LOG.info("Pruning of stale runs whose storage went away finished.")


def remove_unused_files(session):
    LOG.info("Garbage collection of dangling files started...")

    bpe_files = session.query(BugPathEvent.file_id) \
        .group_by(BugPathEvent.file_id) \
        .subquery()
    brp_files = session.query(BugReportPoint.file_id) \
        .group_by(BugReportPoint.file_id) \
        .subquery()

    session.query(File) \
        .filter(File.id.notin_(bpe_files),
                File.id.notin_(brp_files)) \
        .delete(synchronize_session=False)

    files = session.query(File.content_hash) \
        .group_by(File.content_hash) \
        .subquery()

    session.query(FileContent) \
        .filter(FileContent.content_hash.notin_(files)) \
        .delete(synchronize_session=False)

    LOG.info("Garbage collection of dangling files finished.")
