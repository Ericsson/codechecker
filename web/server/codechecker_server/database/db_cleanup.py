# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Contains housekeeping routines that are used to remove expired, obsolete,
or dangling records from the database.
"""
from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy.sql.expression import bindparam, union_all, select, cast

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Severity

from codechecker_common import util
from codechecker_common.logger import get_logger

from .database import DBSession
from .run_db_model import AnalysisInfo, BugPathEvent, BugReportPoint, \
    Comment, File, FileContent, Report, ReportAnalysisInfo, \
    RunHistoryAnalysisInfo, RunLock

LOG = get_logger('server')
RUN_LOCK_TIMEOUT_IN_DATABASE = 30 * 60  # 30 minutes.
SQLITE_LIMIT_COMPOUND_SELECT = 500


def remove_expired_run_locks(session_maker):
    LOG.debug("Garbage collection of expired run locks started...")

    with DBSession(session_maker) as session:
        try:
            locks_expired_at = datetime.now() - timedelta(
                seconds=RUN_LOCK_TIMEOUT_IN_DATABASE)

            session.query(RunLock) \
                .filter(RunLock.locked_at < locks_expired_at) \
                .delete(synchronize_session=False)

            session.commit()

            LOG.debug("Garbage collection of expired run locks finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove expired run locks: %s", str(ex))


def remove_unused_files(session_maker):
    LOG.debug("Garbage collection of dangling files started...")

    # File deletion is a relatively slow operation due to database cascades.
    # Removing files in big chunks prevents reaching a potential database
    # statement timeout. This hard-coded value is a safe choice according to
    # some measurements. Maybe this could be a command-line parameter. But in
    # the long terms we are planning to reduce cascade deletes by redesigning
    # bug_path_events and bug_report_points tables.
    CHUNK_SIZE = 500000

    with DBSession(session_maker) as session:
        try:
            bpe_files = session.query(BugPathEvent.file_id) \
                .group_by(BugPathEvent.file_id) \
                .subquery()
            brp_files = session.query(BugReportPoint.file_id) \
                .group_by(BugReportPoint.file_id) \
                .subquery()

            files_to_delete = session.query(File.id) \
                .filter(File.id.notin_(bpe_files), File.id.notin_(brp_files))
            files_to_delete = map(lambda x: x[0], files_to_delete)

            for chunk in util.chunks(iter(files_to_delete), CHUNK_SIZE):
                session.query(File) \
                    .filter(File.id.in_(chunk)) \
                    .delete(synchronize_session=False)

            files = session.query(File.content_hash) \
                .group_by(File.content_hash) \
                .subquery()

            session.query(FileContent) \
                .filter(FileContent.content_hash.notin_(files)) \
                .delete(synchronize_session=False)

            session.commit()

            LOG.debug("Garbage collection of dangling files finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove unused files: %s", str(ex))


def remove_unused_data(session_maker):
    """ Remove dangling data (files, comments, etc.) from the database. """
    remove_unused_files(session_maker)
    remove_unused_comments(session_maker)
    remove_unused_analysis_info(session_maker)


def remove_unused_comments(session_maker):
    """ Remove dangling comments from the database. """
    LOG.debug("Garbage collection of dangling comments started...")

    with DBSession(session_maker) as session:
        try:
            report_hashes = session.query(Report.bug_id) \
                .group_by(Report.bug_id) \
                .subquery()

            session.query(Comment) \
                .filter(Comment.bug_hash.notin_(report_hashes)) \
                .delete(synchronize_session=False)

            session.commit()

            LOG.debug("Garbage collection of dangling comments finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove dangling comments: %s", str(ex))


def upgrade_severity_levels(session_maker, checker_labels):
    """
    Updates the potentially changed severities at the reports.
    """
    LOG.debug("Upgrading severity levels started...")

    severity_map = {}
    for checker in checker_labels.checkers():
        severity_map[checker] = checker_labels.severity(checker)

    for severity_map_small in util.chunks(
            iter(severity_map.items()), SQLITE_LIMIT_COMPOUND_SELECT):
        severity_map_small = dict(severity_map_small)

        with DBSession(session_maker) as session:
            try:
                # Create a sql query from the severity map.
                severity_map_q = union_all(*[
                    select([cast(bindparam('checker_id' + str(i),
                                           str(checker_id))
                            .label('checker_id'), sqlalchemy.String),
                            cast(bindparam('severity' + str(i),
                                           Severity._NAMES_TO_VALUES[
                                               severity_map_small[checker_id]])
                            .label('severity'), sqlalchemy.Integer)])
                    for i, checker_id in enumerate(severity_map_small)]) \
                    .alias('new_severities')

                checker_ids = list(severity_map_small.keys())

                # Get checkers which has been changed.
                changed_checker_q = select(
                    [Report.checker_id, Report.severity]) \
                    .group_by(Report.checker_id, Report.severity) \
                    .where(Report.checker_id.in_(checker_ids)) \
                    .except_(session.query(severity_map_q)) \
                    .alias('changed_severites')

                changed_checkers = session.query(
                    changed_checker_q.c.checker_id,
                    changed_checker_q.c.severity)

                # Update severity levels of checkers.
                if changed_checkers:
                    updated_checker_ids = set()
                    for checker_id, severity_old in changed_checkers:
                        severity_new = severity_map_small[checker_id]
                        severity_id = Severity._NAMES_TO_VALUES[severity_new]

                        LOG.info("Upgrading severity level of '%s' checker "
                                 "from %s to %s",
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
            except (sqlalchemy.exc.OperationalError,
                    sqlalchemy.exc.ProgrammingError) as ex:
                LOG.error("Failed to upgrade severity levels: %s", str(ex))


def remove_unused_analysis_info(session_maker):
    """ Remove unused analysis information from the database. """
    LOG.debug("Garbage collection of dangling analysis info started...")

    with DBSession(session_maker) as session:
        try:
            run_history_analysis_info = session \
                .query(RunHistoryAnalysisInfo.c.analysis_info_id.distinct()) \
                .subquery()

            report_analysis_info = session \
                .query(ReportAnalysisInfo.c.analysis_info_id.distinct()) \
                .subquery()

            session.query(AnalysisInfo) \
                .filter(AnalysisInfo.id.notin_(run_history_analysis_info),
                        AnalysisInfo.id.notin_(report_analysis_info)) \
                .delete(synchronize_session=False)

            session.commit()

            LOG.debug("Garbage collection of dangling analysis info finished.")
        except (sqlalchemy.exc.OperationalError,
                sqlalchemy.exc.ProgrammingError) as ex:
            LOG.error("Failed to remove dangling analysis info: %s", str(ex))
