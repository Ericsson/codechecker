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

import sqlalchemy
from sqlalchemy.sql.expression import bindparam, union_all, select, cast

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Severity

from codechecker_common.logger import get_logger

from .run_db_model import BugPathEvent, BugReportPoint, File, \
    FileContent, Report, RunLock

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


def upgrade_severity_levels(session, severity_map):
    """
    Updates the potentially changed severities at the reports.
    """
    LOG.debug("Upgrading severity levels started...")

    # Create a sql query from the severity map.
    severity_map_q = union_all(*[
        select([cast(bindparam('checker_id' + str(i), str(checker_id))
                .label('checker_id'), sqlalchemy.String),
                cast(bindparam('severity' + str(i), Severity._NAMES_TO_VALUES[
                    severity_map[checker_id]])
               .label('severity'), sqlalchemy.Integer)])
        for i, checker_id in enumerate(severity_map)]) \
        .alias('new_severities')

    checker_ids = severity_map.keys()

    # Get checkers which has been changed.
    changed_checker_q = select([Report.checker_id, Report.severity]) \
        .group_by(Report.checker_id, Report.severity) \
        .where(Report.checker_id.in_(checker_ids)) \
        .except_(session.query(severity_map_q)).alias('changed_severites')

    changed_checkers = session.query(changed_checker_q.c.checker_id,
                                     changed_checker_q.c.severity)

    # Update severity levels of checkers.
    if changed_checkers:
        updated_checker_ids = set()
        for checker_id, severity_old in changed_checkers:
            severity_new = severity_map.get(checker_id, 'UNSPECIFIED')
            severity_id = Severity._NAMES_TO_VALUES[severity_new]

            LOG.info("Upgrading severity level of '%s' checker from %s to %s",
                     checker_id,
                     Severity._VALUES_TO_NAMES[severity_old],
                     severity_new)

            if checker_id in updated_checker_ids:
                continue

            session.query(Report) \
                .filter(Report.checker_id == checker_id) \
                .update({Report.severity: severity_id})

            updated_checker_ids.add(checker_id)

        session.commit()

    LOG.debug("Upgrading of severity levels finished...")
