# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Contains housekeeping routines that are used to remove expired, obsolete,
or dangling records from the database.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from datetime import datetime, timedelta

from codeCheckerDBAccess_v6.ttypes import *

from libcodechecker.logger import get_logger

from .run_db_model import *

LOG = get_logger('server')
RUN_LOCK_TIMEOUT_IN_DATABASE = 30 * 60  # 30 minutes.


def remove_expired_run_locks(session):
    LOG.debug("Garbage collection of expired run locks started...")

    locks_expired_at = datetime.now() - timedelta(
        seconds=RUN_LOCK_TIMEOUT_IN_DATABASE)

    session.query(RunLock) \
        .filter(RunLock.locked_at < locks_expired_at) \
        .delete(synchronize_session=False)

    LOG.debug("Garbage collection of expired run locks finished.")


def remove_unused_files(session):
    LOG.debug("Garbage collection of dangling files started...")

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

    LOG.debug("Garbage collection of dangling files finished.")
