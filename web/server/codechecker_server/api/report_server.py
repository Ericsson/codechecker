# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import base64
import codecs
from collections import defaultdict
from datetime import datetime, timedelta
import io
import os
import re
import tempfile
import zipfile
import zlib

import sqlalchemy
from sqlalchemy.sql.expression import or_, and_, not_, func, \
    asc, desc, text, union_all, select, bindparam, literal_column, cast

import shared
from codeCheckerDBAccess_v6 import constants, ttypes
from codeCheckerDBAccess_v6.ttypes import BugPathPos, CheckerCount, \
    CommentData, DiffType, Encoding, RunHistoryData, Order, ReportData, \
    ReportDetails, ReviewData, RunData, RunFilter, RunReportCount, \
    RunTagCount, SourceComponentData, SourceFileData, SortMode, SortType

from codechecker_common import plist_parser, skiplist_handler
from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler, SKIP_REVIEW_STATUSES
from codechecker_common import util
from codechecker_common.logger import get_logger
from codechecker_common.profiler import timeit
from codechecker_common.report import get_report_path_hash

from .. import permissions
from ..database import db_cleanup
from ..database.config_db_model import Product
from ..database.database import conv
from ..database.run_db_model import \
    AnalyzerStatistic, Report, ReviewStatus, File, Run, RunHistory, \
    RunLock, Comment, BugPathEvent, BugReportPoint, \
    FileContent, SourceComponent, ExtendedReportData
from ..tmp import TemporaryDirectory

from .db import DBSession, escape_like
from .thrift_enum_helper import detection_status_enum, \
    detection_status_str, review_status_enum, review_status_str, \
    report_extended_data_type_enum

from . import store_handler

LOG = get_logger('server')


def verify_limit_range(limit):
    """Verify limit value for the queries.

    Query limit should not be larger than the max allowed value.
    Max is returned if the value is larger than max.
    """
    max_query_limit = constants.MAX_QUERY_SIZE
    if limit > max_query_limit:
        LOG.warning('Query limit %d was larger than max query limit %d, '
                    'setting limit to %d', limit, max_query_limit, max)
        limit = max_query_limit
    return limit


def slugify(text):
    """
    Removes and replaces special characters in a given text.
    """
    # Removes non-alpha characters.
    norm_text = re.sub(r'[^\w\s\-/]', '', text)

    # Converts spaces and slashes to underscores.
    norm_text = re.sub(r'([\s]+|[/]+)', '_', norm_text)

    return norm_text


def exc_to_thrift_reqfail(func):
    """
    Convert internal exceptions to RequestFailed exception
    which can be sent back on the thrift connections.
    """
    func_name = func.__name__

    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            return res

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            # Convert SQLAlchemy exceptions.
            msg = str(alchemy_ex)
            LOG.warning("%s:\n%s", func_name, msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        except shared.ttypes.RequestFailed as rf:
            LOG.warning(rf.message)
            raise
        except Exception as ex:
            msg = str(ex)
            LOG.warning(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.GENERAL,
                                              msg)

    return wrapper


def get_component_values(session, component_name):
    """
    Get component values by component names and returns a tuple where the
    first item contains a list path which should be skipped and the second
    item contains a list of path which should be included.
    E.g.:
      +/a/b/x.cpp
      +/a/b/y.cpp
      -/a/b
    On the above component value this function will return the following:
      (['/a/b'], ['/a/b/x.cpp', '/a/b/y.cpp'])
    """
    components = session.query(SourceComponent) \
        .filter(SourceComponent.name.like(component_name)) \
        .all()

    skip = []
    include = []

    for component in components:
        values = component.value.split('\n')
        for value in values:
            v = value[1:].strip()
            if value[0] == '+':
                include.append(v)
            elif value[0] == '-':
                skip.append(v)

    return skip, include


def process_report_filter(session, report_filter):
    """
    Process the new report filter.
    """

    if report_filter is None:
        return text('')

    AND = []
    if report_filter.filepath:
        OR = [File.filepath.ilike(conv(fp))
              for fp in report_filter.filepath]

        AND.append(or_(*OR))

    if report_filter.checkerMsg:
        OR = [Report.checker_message.ilike(conv(cm))
              for cm in report_filter.checkerMsg]
        AND.append(or_(*OR))

    if report_filter.checkerName:
        OR = [Report.checker_id.ilike(conv(cn))
              for cn in report_filter.checkerName]
        AND.append(or_(*OR))

    if report_filter.runName:
        OR = [Run.name.ilike(conv(rn))
              for rn in report_filter.runName]
        AND.append(or_(*OR))

    if report_filter.reportHash:
        OR = [Report.bug_id.ilike(conv(rh))
              for rh in report_filter.reportHash]
        AND.append(or_(*OR))

    if report_filter.severity:
        AND.append(Report.severity.in_(report_filter.severity))

    if report_filter.detectionStatus:
        dst = list(map(detection_status_str,
                       report_filter.detectionStatus))
        AND.append(Report.detection_status.in_(dst))

    if report_filter.reviewStatus:
        OR = [ReviewStatus.status.in_(
            list(map(review_status_str, report_filter.reviewStatus)))]

        # No database entry for unreviewed reports
        if (ttypes.ReviewStatus.UNREVIEWED in
                report_filter.reviewStatus):
            OR.append(ReviewStatus.status.is_(None))

        AND.append(or_(*OR))

    detection_status = report_filter.detectionStatus
    if report_filter.firstDetectionDate is not None:
        date = datetime.fromtimestamp(report_filter.firstDetectionDate)

        OR = []
        if detection_status is not None and len(detection_status) == 1 and \
           ttypes.DetectionStatus.RESOLVED in detection_status:
            OR.append(Report.fixed_at >= date)
        else:
            OR.append(Report.detected_at >= date)
        AND.append(or_(*OR))

    if report_filter.fixDate is not None:
        date = datetime.fromtimestamp(report_filter.fixDate)

        OR = []
        if detection_status is not None and len(detection_status) == 1 and \
           ttypes.DetectionStatus.RESOLVED in detection_status:
            OR.append(Report.fixed_at < date)
        else:
            OR.append(Report.detected_at < date)
        AND.append(or_(*OR))

    if report_filter.runHistoryTag:
        OR = []
        for history_date in report_filter.runHistoryTag:
            date = datetime.strptime(history_date,
                                     '%Y-%m-%d %H:%M:%S.%f')
            OR.append(and_(Report.detected_at <= date, or_(
                Report.fixed_at.is_(None), Report.fixed_at >= date)))
        AND.append(or_(*OR))

    if report_filter.runTag:
        OR = []
        for tag_id in report_filter.runTag:
            history = session.query(RunHistory).get(tag_id)

            OR.append(and_(Report.run_id == history.run_id,
                           and_(Report.detected_at <= history.time,
                                or_(Report.fixed_at.is_(None),
                                    Report.fixed_at >= history.time))))
        AND.append(or_(*OR))

    if report_filter.componentNames:
        OR = []

        for component_name in report_filter.componentNames:
            skip, include = get_component_values(session, component_name)

            skip_q, include_q = None, None

            if include:
                and_q = [File.filepath.like(conv(fp)) for fp in include]
                include_q = select([File.id]).where(or_(*and_q))

            if skip:
                and_q = [(File.filepath.like(conv(fp))) for fp in skip]
                skip_q = select([File.id]).where(or_(*and_q))

            file_ids = []
            if skip and include:
                skip_q = include_q.except_(skip_q).alias('component')
                file_ids = session.query(skip_q) \
                    .distinct() \
                    .all()
            elif include:
                file_ids = session.query(include_q.alias('include')).all()
            elif skip:
                and_q = [not_(File.filepath.like(conv(fp))) for fp in skip]
                skip_q = select([File.id]).where(and_(*and_q))
                file_ids = session.query(skip_q.alias('skip')).all()

            if file_ids:
                OR.append(or_(File.id.in_([f_id[0] for f_id in file_ids])))
            else:
                # File id list can be empty for example when the user skips
                # everything.
                OR.append(False)

        AND.append(or_(*OR))

    filter_expr = and_(*AND)
    return filter_expr


def process_run_history_filter(query, run_ids, run_history_filter):
    """
    Process run history filter.
    """
    if run_ids:
        query = query.filter(RunHistory.run_id.in_(run_ids))

    if run_history_filter and run_history_filter.tagNames:
        query = query.filter(RunHistory.version_tag.in_(
            run_history_filter.tagNames))

    return query


def process_run_filter(query, run_filter):
    """
    Process run filter.
    """
    if run_filter is None:
        return query

    if run_filter.ids:
        query = query.filter(Run.id.in_(run_filter.ids))
    if run_filter.names:
        if run_filter.exactMatch:
            query = query.filter(Run.name.in_(run_filter.names))
        else:
            OR = [Run.name.ilike('{0}'.format(conv(
                escape_like(name, '\\'))), escape='\\') for
                name in run_filter.names]
            query = query.filter(or_(*OR))

    return query


def get_diff_hashes_for_query(base_run_ids, base_line_hashes, new_run_ids,
                              new_check_hashes, diff_type):
    """
    Get the report hash list for the result comparison.

    Returns the list of hashes (NEW, RESOLVED, UNRESOLVED) and
    the run ids which should be queried for the reports.
    """
    if diff_type == DiffType.NEW:
        df = [] + list(new_check_hashes.difference(base_line_hashes))
        return df, new_run_ids

    elif diff_type == DiffType.RESOLVED:
        df = [] + list(base_line_hashes.difference(new_check_hashes))
        return df, base_run_ids

    elif diff_type == DiffType.UNRESOLVED:
        df = [] + list(base_line_hashes.intersection(new_check_hashes))
        return df, new_run_ids
    else:
        msg = 'Unsupported diff type: ' + str(diff_type)
        LOG.error(msg)
        raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                          msg)


def get_report_details(session, report_ids):
    """
    Returns report details for the given report ids.
    """
    details = {}

    # Get bug path events.
    bug_path_events = session.query(BugPathEvent, File.filepath) \
        .filter(BugPathEvent.report_id.in_(report_ids)) \
        .outerjoin(File,
                   File.id == BugPathEvent.file_id) \
        .order_by(BugPathEvent.report_id, BugPathEvent.order)

    bug_events_list = defaultdict(list)
    for event, file_path in bug_path_events:
        report_id = event.report_id
        event = bugpathevent_db_to_api(event)
        event.filePath = file_path
        bug_events_list[report_id].append(event)

    # Get bug report points.
    bug_report_points = session.query(BugReportPoint, File.filepath) \
        .filter(BugReportPoint.report_id.in_(report_ids)) \
        .outerjoin(File,
                   File.id == BugReportPoint.file_id) \
        .order_by(BugReportPoint.report_id, BugReportPoint.order)

    bug_point_list = defaultdict(list)
    for bug_point, file_path in bug_report_points:
        report_id = bug_point.report_id
        bug_point = bugreportpoint_db_to_api(bug_point)
        bug_point.filePath = file_path
        bug_point_list[report_id].append(bug_point)

    # Get extended report data.
    extended_data_list = defaultdict(list)
    q = session.query(ExtendedReportData, File.filepath) \
        .filter(ExtendedReportData.report_id.in_(report_ids)) \
        .outerjoin(File,
                   File.id == ExtendedReportData.file_id)

    for data, file_path in q:
        report_id = data.report_id
        extended_data = extended_data_db_to_api(data)
        extended_data.filePath = file_path
        extended_data_list[report_id].append(extended_data)

    for report_id in report_ids:
        details[report_id] = \
            ReportDetails(pathEvents=bug_events_list[report_id],
                          executionPath=bug_point_list[report_id],
                          extendedData=extended_data_list[report_id])

    return details


def bugpathevent_db_to_api(bpe):
    return ttypes.BugPathEvent(
        startLine=bpe.line_begin,
        startCol=bpe.col_begin,
        endLine=bpe.line_end,
        endCol=bpe.col_end,
        msg=bpe.msg,
        fileId=bpe.file_id)


def bugreportpoint_db_to_api(brp):
    return BugPathPos(
        startLine=brp.line_begin,
        startCol=brp.col_begin,
        endLine=brp.line_end,
        endCol=brp.col_end,
        fileId=brp.file_id)


def extended_data_db_to_api(erd):
    return ttypes.ExtendedReportData(
        type=report_extended_data_type_enum(erd.type),
        startLine=erd.line_begin,
        startCol=erd.col_begin,
        endLine=erd.line_end,
        endCol=erd.col_end,
        message=erd.message,
        fileId=erd.file_id)


def unzip(b64zip, output_dir):
    """
    This function unzips the base64 encoded zip file. This zip is extracted
    to a temporary directory and the ZIP is then deleted. The function returns
    the name of the extracted directory.
    """
    with tempfile.NamedTemporaryFile(suffix='.zip') as zip_file:
        LOG.debug("Unzipping mass storage ZIP '%s' to '%s'...",
                  zip_file.name, output_dir)

        zip_file.write(zlib.decompress(base64.b64decode(b64zip)))
        with zipfile.ZipFile(zip_file, 'r', allowZip64=True) as zipf:
            try:
                zipf.extractall(output_dir)
            except Exception:
                LOG.error("Failed to extract received ZIP.")
                import traceback
                traceback.print_exc()
                raise


def create_review_data(review_status):
    if review_status:
        return ReviewData(status=review_status_enum(review_status.status),
                          comment=review_status.message,
                          author=review_status.author,
                          date=str(review_status.date))
    else:
        return ReviewData(status=ttypes.ReviewStatus.UNREVIEWED)


def create_count_expression(report_filter):
    if report_filter is not None and report_filter.isUnique:
        return func.count(Report.bug_id.distinct())
    else:
        return func.count(literal_column('*'))


def filter_report_filter(q, filter_expression, run_ids=None, cmp_data=None,
                         diff_hashes=None):
    if run_ids:
        q = q.filter(Report.run_id.in_(run_ids))

    q = q.outerjoin(File,
                    Report.file_id == File.id) \
        .outerjoin(ReviewStatus,
                   ReviewStatus.bug_hash == Report.bug_id) \
        .filter(filter_expression)

    if cmp_data:
        q = q.filter(Report.bug_id.in_(diff_hashes))

    return q


def get_sort_map(sort_types, is_unique=False):
    # Get a list of sort_types which will be a nested ORDER BY.
    sort_type_map = {
        SortType.FILENAME: [(File.filepath, 'filepath'),
                            (Report.line, 'line')],
        SortType.BUG_PATH_LENGTH: [(Report.path_length, 'bug_path_length')],
        SortType.CHECKER_NAME: [(Report.checker_id, 'checker_id')],
        SortType.SEVERITY: [(Report.severity, 'severity')],
        SortType.REVIEW_STATUS: [(ReviewStatus.status, 'rw_status')],
        SortType.DETECTION_STATUS: [(Report.detection_status, 'dt_status')]}

    if is_unique:
        sort_type_map[SortType.FILENAME] = [(File.filename, 'filename')]
        sort_type_map[SortType.DETECTION_STATUS] = []

    # Mapping the SQLAlchemy functions.
    order_type_map = {Order.ASC: asc, Order.DESC: desc}

    if sort_types is None:
        sort_types = [SortMode(SortType.SEVERITY, Order.DESC)]

    return sort_types, sort_type_map, order_type_map


def sort_results_query(query, sort_types, sort_type_map, order_type_map,
                       order_by_label=False):
    """
    Helper method for __queryDiffResults and queryResults to apply sorting.
    """
    for sort in sort_types:
        sorttypes = sort_type_map.get(sort.type)
        for sorttype in sorttypes:
            order_type = order_type_map.get(sort.ord)
            sort_col = sorttype[1] if order_by_label else sorttype[0]
            query = query.order_by(order_type(sort_col))

    return query


def filter_unresolved_reports(q):
    """
    Filter reports which are unresolved.

    Note: review status of these reports are not in the SKIP_REVIEW_STATUSES
    list and detection statuses are not in skip_detection_statuses.
    """
    skip_review_status = SKIP_REVIEW_STATUSES
    skip_detection_statuses = ['resolved', 'off', 'unavailable']

    return q.filter(Report.detection_status.notin_(skip_detection_statuses)) \
            .filter(or_(ReviewStatus.status.is_(None),
                        ReviewStatus.status.notin_(skip_review_status))) \
            .outerjoin(ReviewStatus,
                       ReviewStatus.bug_hash == Report.bug_id)


def get_report_hashes(session, run_ids, tag_ids):
    """
    Get report hash list for the reports which can be found in the given runs
    and the given tags.
    """
    q = session.query(Report.bug_id)

    if run_ids:
        q = q.filter(Report.run_id.in_(run_ids))

    if tag_ids:
        q = q.outerjoin(RunHistory,
                        RunHistory.run_id == Report.run_id) \
            .filter(RunHistory.id.in_(tag_ids)) \
            .filter(Report.detected_at <= RunHistory.time) \
            .filter(or_(Report.fixed_at.is_(None),
                        Report.fixed_at > RunHistory.time))

    return set([t[0] for t in q])


def check_remove_runs_lock(session, run_ids):
    """
    Check if there is an existing lock on the given runs, which has not
    expired yet. If so, the run cannot be deleted, as someone is assumed to
    be storing into it.
    """
    locks_expired_at = datetime.now() - timedelta(
        seconds=db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE)

    run_locks = session.query(RunLock.name) \
        .filter(RunLock.locked_at >= locks_expired_at)

    if run_ids:
        run_locks = run_locks.filter(Run.id.in_(run_ids))

    run_locks = run_locks \
        .outerjoin(Run,
                   Run.name == RunLock.name) \
        .all()

    if run_locks:
        raise shared.ttypes.RequestFailed(
            shared.ttypes.ErrorCode.DATABASE,
            "Can not remove results because the following runs "
            "are locked: {0}".format(
                ', '.join([r[0] for r in run_locks])))


class ThriftRequestHandler(object):
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 manager,
                 Session,
                 product,
                 auth_session,
                 config_database,
                 checker_md_docs,
                 checker_md_docs_map,
                 src_comment_handler,
                 package_version,
                 context):

        if not product:
            raise ValueError("Cannot initialize request handler without "
                             "a product to serve.")

        self.__manager = manager
        self.__product = product
        self.__auth_session = auth_session
        self.__config_database = config_database
        self.__checker_md_docs = checker_md_docs
        self.__checker_doc_map = checker_md_docs_map
        self.__src_comment_handler = src_comment_handler
        self.__package_version = package_version
        self.__Session = Session
        self.__context = context
        self.__permission_args = {
            'productID': product.id
        }

    def __get_username(self):
        """
        Returns the actually logged in user name.
        """
        return self.__auth_session.user if self.__auth_session else "Anonymous"

    def __require_permission(self, required):
        """
        Helper method to raise an UNAUTHORIZED exception if the user does not
        have any of the given permissions.
        """

        with DBSession(self.__config_database) as session:
            args = dict(self.__permission_args)
            args['config_db_session'] = session

            if not any([permissions.require_permission(
                            perm, args, self.__auth_session)
                        for perm in required]):
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You are not authorized to execute this action.")

            return True

    def __require_admin(self):
        self.__require_permission([permissions.PRODUCT_ADMIN])

    def __require_access(self):
        self.__require_permission([permissions.PRODUCT_ACCESS])

    def __require_store(self):
        self.__require_permission([permissions.PRODUCT_STORE])

    @staticmethod
    def __get_run_ids_to_query(session, cmp_data=None):
        """
        Return run id list for the queries.
        If compare data is set remove those run ids from the returned list.
        The returned run id list can be used as a baseline for comparisons.
        """
        res = session.query(Run.id).all()
        run_ids = [r[0] for r in res]
        if cmp_data:
            all_rids = set(run_ids)
            cmp_rids = set(cmp_data.runIds) if cmp_data.runIds else set()
            run_ids = list(all_rids.difference(cmp_rids))

        return run_ids

    @exc_to_thrift_reqfail
    @timeit
    def getRunData(self, run_filter, limit, offset):
        self.__require_access()

        limit = verify_limit_range(limit)

        with DBSession(self.__Session) as session:

            # Count the reports subquery.
            stmt = session.query(Report.run_id,
                                 func.count(Report.bug_id)
                                 .label('report_count'))

            stmt = filter_unresolved_reports(stmt) \
                .group_by(Report.run_id).subquery()

            tag_q = session.query(RunHistory.run_id,
                                  func.max(RunHistory.id).label(
                                      'run_history_id'),
                                  func.max(RunHistory.time).label(
                                      'run_history_time')) \
                .group_by(RunHistory.run_id) \
                .subquery()

            q = session.query(Run,
                              RunHistory.version_tag,
                              RunHistory.cc_version,
                              stmt.c.report_count)

            q = process_run_filter(q, run_filter)

            q = q.outerjoin(stmt, Run.id == stmt.c.run_id) \
                .outerjoin(tag_q, Run.id == tag_q.c.run_id) \
                .outerjoin(RunHistory,
                           RunHistory.id == tag_q.c.run_history_id) \
                .group_by(Run.id,
                          RunHistory.version_tag,
                          RunHistory.cc_version,
                          stmt.c.report_count) \
                .order_by(Run.date)

            if limit:
                q = q.limit(limit).offset(offset)

            # Get the runs.
            run_data = q.all()

            # Set run ids filter by using the previous results.
            if not run_filter:
                run_filter = RunFilter()

            run_filter.ids = [r[0].id for r in run_data]

            # Get report count for each detection statuses.
            status_q = session.query(Report.run_id,
                                     Report.detection_status,
                                     func.count(Report.bug_id))

            if run_filter and run_filter.ids is not None:
                status_q = status_q.filter(Report.run_id.in_(run_filter.ids))

            status_q = status_q.group_by(Report.run_id,
                                         Report.detection_status)

            status_sum = defaultdict(defaultdict)
            for run_id, status, count in status_q:
                status_sum[run_id][detection_status_enum(status)] = count

            # Get analyzer statistics.
            analyzer_statistics = defaultdict(lambda: defaultdict())
            stat_q = session.query(AnalyzerStatistic,
                                   Run.id)

            if run_filter and run_filter.ids is not None:
                stat_q = stat_q.filter(Run.id.in_(run_filter.ids))

            stat_q = stat_q \
                .outerjoin(RunHistory,
                           RunHistory.id == AnalyzerStatistic.run_history_id) \
                .outerjoin(Run,
                           Run.id == RunHistory.run_id)

            for stat, run_id in stat_q:
                failed_files = zlib.decompress(stat.failed_files).split('\n') \
                    if stat.failed_files else None
                analyzer_version = zlib.decompress(stat.version) \
                    if stat.version else None

                analyzer_statistics[run_id][stat.analyzer_type] = \
                    ttypes.AnalyzerStatistics(version=analyzer_version,
                                              failed=stat.failed,
                                              failedFilePaths=failed_files,
                                              successful=stat.successful)

            results = []

            for instance, tag, cc_version, report_count in run_data:
                if report_count is None:
                    report_count = 0

                results.append(RunData(instance.id,
                                       str(instance.date),
                                       instance.name,
                                       instance.duration,
                                       report_count,
                                       instance.command,
                                       status_sum[instance.id],
                                       tag,
                                       cc_version,
                                       analyzer_statistics[instance.id]))
            return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunCount(self, run_filter):
        self.__require_access()

        with DBSession(self.__Session) as session:
            query = session.query(Run.id)
            query = process_run_filter(query, run_filter)

        return query.count()

    @exc_to_thrift_reqfail
    @timeit
    def getRunHistory(self, run_ids, limit, offset, run_history_filter):
        self.__require_access()

        limit = verify_limit_range(limit)

        with DBSession(self.__Session) as session:

            res = session.query(RunHistory)

            res = process_run_history_filter(res, run_ids, run_history_filter)

            res = res.order_by(RunHistory.time.desc())

            if limit:
                res = res.limit(limit).offset(offset)

            results = []
            for history in res:
                check_command = zlib.decompress(history.check_command) \
                  if history.check_command else None

                analyzer_statistics = {}
                for stat in history.analyzer_statistics:
                    failed_files = zlib.decompress(stat.failed_files) \
                        .split('\n') if stat.failed_files else None
                    analyzer_version = zlib.decompress(stat.version) \
                        if stat.version else None

                    analyzer_statistics[stat.analyzer_type] = \
                        ttypes.AnalyzerStatistics(
                            version=analyzer_version,
                            failed=stat.failed,
                            failedFilePaths=failed_files,
                            successful=stat.successful)

                results.append(RunHistoryData(
                    id=history.id,
                    runId=history.run.id,
                    runName=history.run.name,
                    versionTag=history.version_tag,
                    user=history.user,
                    time=str(history.time),
                    checkCommand=check_command,
                    codeCheckerVersion=history.cc_version,
                    analyzerStatistics=analyzer_statistics))

            return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunHistoryCount(self, run_ids, run_history_filter):
        self.__require_access()

        with DBSession(self.__Session) as session:
            query = session.query(RunHistory.id)
            query = process_run_history_filter(query,
                                               run_ids,
                                               run_history_filter)

        return query.count()

    @exc_to_thrift_reqfail
    @timeit
    def getReport(self, reportId):
        self.__require_access()

        with DBSession(self.__Session) as session:

            result = session.query(Report,
                                   File,
                                   ReviewStatus) \
                .filter(Report.id == reportId) \
                .outerjoin(File, Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .limit(1).one_or_none()

            if not result:
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE,
                    "Report " + str(reportId) + " not found!")

            report, source_file, review_status = result
            return ReportData(
                runId=report.run_id,
                bugHash=report.bug_id,
                checkedFile=source_file.filepath,
                checkerMsg=report.checker_message,
                reportId=report.id,
                fileId=source_file.id,
                line=report.line,
                column=report.column,
                checkerId=report.checker_id,
                severity=report.severity,
                reviewData=create_review_data(review_status),
                detectionStatus=detection_status_enum(report.detection_status),
                detectedAt=str(report.detected_at),
                fixedAt=str(report.fixed_at) if report.fixed_at else None)

    @exc_to_thrift_reqfail
    @timeit
    def getDiffResultsHash(self, run_ids, report_hashes, diff_type):
        self.__require_access()

        with DBSession(self.__Session) as session:
            if diff_type == DiffType.NEW:
                # In postgresql we can select multiple rows filled with
                # constants by using `unnest` function. In sqlite we have to
                # use multiple UNION ALL.

                if not report_hashes:
                    return []

                base_hashes = session.query(Report.bug_id.label('bug_id')) \
                    .outerjoin(File, Report.file_id == File.id)

                if run_ids:
                    base_hashes = \
                        base_hashes.filter(Report.run_id.in_(run_ids))

                if self.__product.driver_name == 'postgresql':
                    new_hashes = select([func.unnest(report_hashes)
                                        .label('bug_id')]) \
                        .except_(base_hashes).alias('new_bugs')
                    return [res[0] for res in session.query(new_hashes)]
                else:
                    # The maximum number of compound select in sqlite is 500
                    # by default. We increased SQLITE_MAX_COMPOUND_SELECT
                    # limit but when the number of compound select was larger
                    # than 8435 sqlite threw a `Segmentation fault` error.
                    # For this reason we create queries with chunks.
                    new_hashes = []
                    chunk_size = 500
                    for chunk in [report_hashes[i:i + chunk_size] for
                                  i in range(0, len(report_hashes),
                                             chunk_size)]:
                        new_hashes_query = union_all(*[
                            select([bindparam('bug_id' + str(i), h)
                                   .label('bug_id')])
                            for i, h in enumerate(chunk)])
                        q = select([new_hashes_query]).except_(base_hashes)
                        new_hashes.extend([res[0] for res in session.query(q)])

                    return new_hashes
            elif diff_type == DiffType.RESOLVED:
                results = session.query(Report.bug_id) \
                    .filter(Report.bug_id.notin_(report_hashes))

                if run_ids:
                    results = results.filter(Report.run_id.in_(run_ids))

                return [res[0] for res in results]

            elif diff_type == DiffType.UNRESOLVED:
                results = session.query(Report.bug_id) \
                    .filter(Report.bug_id.in_(report_hashes))

                if run_ids:
                    results = results.filter(Report.run_id.in_(run_ids))

                return [res[0] for res in results]

            else:
                return []

    @exc_to_thrift_reqfail
    @timeit
    def getRunResults(self, run_ids, limit, offset, sort_types,
                      report_filter, cmp_data, get_details):
        self.__require_access()

        limit = verify_limit_range(limit)

        with DBSession(self.__Session) as session:
            results = []

            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                sort_types, sort_type_map, order_type_map = \
                    get_sort_map(sort_types, True)

                selects = [func.max(Report.id).label('id')]
                for sort in sort_types:
                    sorttypes = sort_type_map.get(sort.type)
                    for sorttype in sorttypes:
                        if sorttype[0] != 'bug_path_length':
                            selects.append(func.max(sorttype[0])
                                           .label(sorttype[1]))

                unique_reports = session.query(*selects)
                unique_reports = filter_report_filter(unique_reports,
                                                      filter_expression,
                                                      run_ids,
                                                      cmp_data,
                                                      diff_hashes)
                unique_reports = unique_reports \
                    .group_by(Report.bug_id) \
                    .subquery()

                # Sort the results
                sorted_reports = \
                    session.query(unique_reports.c.id)

                sorted_reports = sort_results_query(sorted_reports,
                                                    sort_types,
                                                    sort_type_map,
                                                    order_type_map,
                                                    True)

                sorted_reports = sorted_reports \
                    .limit(limit).offset(offset).subquery()

                q = session.query(Report.id, Report.bug_id,
                                  Report.checker_message, Report.checker_id,
                                  Report.severity, Report.detected_at,
                                  Report.fixed_at, ReviewStatus,
                                  File.filename, File.filepath,
                                  Report.path_length) \
                    .outerjoin(File, Report.file_id == File.id) \
                    .outerjoin(ReviewStatus,
                               ReviewStatus.bug_hash == Report.bug_id) \
                    .outerjoin(sorted_reports,
                               sorted_reports.c.id == Report.id) \
                    .filter(sorted_reports.c.id.isnot(None))

                # We have to sort the results again because an ORDER BY in a
                # subtable is broken by the JOIN.
                q = sort_results_query(q,
                                       sort_types,
                                       sort_type_map,
                                       order_type_map)

                query_result = q.all()

                # Get report details if it is required.
                report_details = {}
                if get_details:
                    report_ids = [r[0] for r in query_result]
                    report_details = get_report_details(session, report_ids)

                for report_id, bug_id, checker_msg, checker, severity, \
                    detected_at, fixed_at, status, filename, path, \
                        bug_path_len in query_result:
                    review_data = create_review_data(status)

                    results.append(
                        ReportData(bugHash=bug_id,
                                   checkedFile=filename,
                                   checkerMsg=checker_msg,
                                   checkerId=checker,
                                   severity=severity,
                                   reviewData=review_data,
                                   detectedAt=str(detected_at),
                                   fixedAt=str(fixed_at),
                                   bugPathLength=bug_path_len,
                                   details=report_details.get(report_id)))
            else:
                q = session.query(Report.run_id, Report.id, Report.file_id,
                                  Report.line, Report.column,
                                  Report.detection_status, Report.bug_id,
                                  Report.checker_message, Report.checker_id,
                                  Report.severity, Report.detected_at,
                                  Report.fixed_at, ReviewStatus,
                                  File.filepath,
                                  Report.path_length) \
                    .outerjoin(File, Report.file_id == File.id) \
                    .outerjoin(ReviewStatus,
                               ReviewStatus.bug_hash == Report.bug_id) \
                    .filter(filter_expression)

                if run_ids:
                    q = q.filter(Report.run_id.in_(run_ids))

                if cmp_data:
                    q = q.filter(Report.bug_id.in_(diff_hashes))

                sort_types, sort_type_map, order_type_map = \
                    get_sort_map(sort_types)

                q = sort_results_query(q, sort_types, sort_type_map,
                                       order_type_map)

                q = q.limit(limit).offset(offset)

                query_result = q.all()

                # Get report details if it is required.
                report_details = {}
                if get_details:
                    report_ids = [r[1] for r in query_result]
                    report_details = get_report_details(session, report_ids)

                for run_id, report_id, file_id, line, column, d_status, \
                    bug_id, checker_msg, checker, severity, detected_at,\
                    fixed_at, r_status, path, bug_path_len \
                        in query_result:

                    review_data = create_review_data(r_status)
                    results.append(
                        ReportData(runId=run_id,
                                   bugHash=bug_id,
                                   checkedFile=path,
                                   checkerMsg=checker_msg,
                                   reportId=report_id,
                                   fileId=file_id,
                                   line=line,
                                   column=column,
                                   checkerId=checker,
                                   severity=severity,
                                   reviewData=review_data,
                                   detectionStatus=detection_status_enum(
                                       d_status),
                                   detectedAt=str(detected_at),
                                   fixedAt=str(fixed_at) if fixed_at else None,
                                   bugPathLength=bug_path_len,
                                   details=report_details.get(report_id)))

            return results

    @timeit
    def getRunReportCounts(self, run_ids, report_filter, limit, offset):
        """
          Count the results separately for multiple runs.
          If an empty run id list is provided the report
          counts will be calculated for all of the available runs.
        """
        self.__require_access()
        results = []
        with DBSession(self.__Session) as session:
            filter_expression = process_report_filter(session, report_filter)

            count_expr = create_count_expression(report_filter)
            q = session.query(Run.id,
                              Run.name,
                              count_expr) \
                .select_from(Report)

            if run_ids:
                q = q.filter(Report.run_id.in_(run_ids))

            q = q.outerjoin(File, Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .outerjoin(Run,
                           Report.run_id == Run.id) \
                .filter(filter_expression) \
                .order_by(Run.name) \
                .group_by(Run.id)

            if limit:
                q = q.limit(limit).offset(offset)

            for run_id, run_name, count in q:
                report_count = RunReportCount(runId=run_id,
                                              name=run_name,
                                              reportCount=count)
                results.append(report_count)

            return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunResultCount(self, run_ids, report_filter, cmp_data):
        self.__require_access()

        with DBSession(self.__Session) as session:
            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return 0

            filter_expression = process_report_filter(session, report_filter)
            q = session.query(Report.bug_id)
            q = filter_report_filter(q, filter_expression, run_ids, cmp_data,
                                     diff_hashes)

            if report_filter is not None and report_filter.isUnique:
                q = q.group_by(Report.bug_id)

            report_count = q.count()
            if report_count is None:
                report_count = 0

            return report_count

    @staticmethod
    @timeit
    def __construct_bug_item_list(session, report_id, item_type):

        q = session.query(item_type) \
            .filter(item_type.report_id == report_id) \
            .order_by(item_type.order)

        bug_items = []

        for event in q:
            f = session.query(File).get(event.file_id)
            bug_items.append((event, f.filepath))

        return bug_items

    @exc_to_thrift_reqfail
    @timeit
    def getReportDetails(self, reportId):
        """
        Parameters:
         - reportId
        """
        self.__require_access()
        with DBSession(self.__Session) as session:
            return get_report_details(session, [reportId])[reportId]

    def _setReviewStatus(self, report_id, status, message, session):
        """
        This function sets the review status of the given report. This is the
        implementation of changeReviewStatus(), but it is also extended with
        a session parameter which represents a database transaction. This is
        needed because during storage a specific session object has to be used.
        """
        self.__require_permission([permissions.PRODUCT_ACCESS,
                                   permissions.PRODUCT_STORE])
        report = session.query(Report).get(report_id)
        if report:
            review_status = session.query(ReviewStatus).get(report.bug_id)
            if review_status is None:
                review_status = ReviewStatus()
                review_status.bug_hash = report.bug_id

            user = self.__get_username()

            review_status.status = review_status_str(status)
            review_status.author = user
            review_status.message = message.encode('utf8')
            review_status.date = datetime.now()

            session.add(review_status)
            session.flush()

            return True
        else:
            msg = "No report found in the database."
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def isReviewStatusChangeDisabled(self):
        """
        Return True if review status change is disabled.
        """
        with DBSession(self.__config_database) as session:
            product = session.query(Product).get(self.__product.id)
            return product.is_review_status_change_disabled

    @exc_to_thrift_reqfail
    @timeit
    def changeReviewStatus(self, report_id, status, message):
        """
        Change review status of the bug by report id.
        """
        if self.isReviewStatusChangeDisabled():
            msg = "Review status change is disabled!"
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL, msg)

        with DBSession(self.__Session) as session:
            res = self._setReviewStatus(report_id, status, message, session)
            session.commit()

            LOG.info("Review status of report '%s' was changed to '%s' by %s.",
                     report_id, review_status_str(status),
                     self.__get_username())

        return res

    @exc_to_thrift_reqfail
    @timeit
    def getComments(self, report_id):
        """
            Return the list of comments for the given bug.
        """
        self.__require_access()

        with DBSession(self.__Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                result = []

                comments = session.query(Comment) \
                    .filter(Comment.bug_hash == report.bug_id) \
                    .order_by(Comment.created_at.desc()) \
                    .all()

                for comment in comments:
                    result.append(CommentData(
                        comment.id,
                        comment.author,
                        comment.message,
                        str(comment.created_at)))

                return result
            else:
                msg = 'Report id ' + str(report_id) + \
                      ' was not found in the database.'
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def getCommentCount(self, report_id):
        """
            Return the number of comments for the given bug.
        """
        self.__require_access()
        with DBSession(self.__Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                commentCount = session.query(Comment) \
                    .filter(Comment.bug_hash == report.bug_id) \
                    .count()

            if commentCount is None:
                commentCount = 0

            return commentCount

    @exc_to_thrift_reqfail
    @timeit
    def addComment(self, report_id, comment_data):
        """
            Add new comment for the given bug.
        """
        self.__require_access()
        with DBSession(self.__Session) as session:
            report = session.query(Report).get(report_id)
            if report:
                user = self.__get_username()
                comment = Comment(report.bug_id,
                                  user,
                                  comment_data.message,
                                  datetime.now())

                session.add(comment)
                session.commit()

                return True
            else:
                msg = 'Report id ' + str(report_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def updateComment(self, comment_id, content):
        """
            Update the given comment message with new content. We allow
            comments to be updated by it's original author only, except for
            Anyonymous comments that can be updated by anybody.
        """
        self.__require_access()
        with DBSession(self.__Session) as session:

            user = self.__get_username()

            comment = session.query(Comment).get(comment_id)
            if comment:
                if comment.author != 'Anonymous' and comment.author != user:
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.UNAUTHORIZED,
                        'Unathorized comment modification!')
                comment.message = content
                session.add(comment)
                session.commit()
                return True
            else:
                msg = 'Comment id ' + str(comment_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def removeComment(self, comment_id):
        """
            Remove the comment. We allow comments to be removed by it's
            original author only, except for Anyonymous comments that can be
            updated by anybody.
        """
        self.__require_access()

        user = self.__get_username()

        with DBSession(self.__Session) as session:

            comment = session.query(Comment).get(comment_id)
            if comment:
                if comment.author != 'Anonymous' and comment.author != user:
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.UNAUTHORIZED,
                        'Unathorized comment modification!')
                session.delete(comment)
                session.commit()

                LOG.info("Comment '%s...' was removed from bug hash '%s' by "
                         "'%s'.", comment.message[:10], comment.bug_hash,
                         self.__get_username())

                return True
            else:
                msg = 'Comment id ' + str(comment_id) + \
                      ' was not found in the database.'
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerDoc(self, checkerId):
        """
        Parameters:
         - checkerId
        """

        missing_doc = "No documentation found for checker: " + checkerId + \
                      "\n\nPlease refer to the documentation at the "

        if "." in checkerId:
            sa_link = "http://clang-analyzer.llvm.org/available_checks.html"
            missing_doc += "[ClangSA](" + sa_link + ")"
        elif "-" in checkerId:
            tidy_link = "http://clang.llvm.org/extra/clang-tidy/checks/" + \
                      checkerId + ".html"
            missing_doc += "[ClangTidy](" + tidy_link + ")"
        missing_doc += " homepage."

        try:
            md_file = self.__checker_doc_map.get(checkerId)
            if md_file:
                md_file = os.path.join(self.__checker_md_docs, md_file)
                try:
                    with io.open(md_file, 'r') as md_content:
                        missing_doc = md_content.read()
                except (IOError, OSError):
                    LOG.warning("Failed to read checker documentation: %s",
                                md_file)

            return missing_doc

        except Exception as ex:
            msg = str(ex)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)

    @exc_to_thrift_reqfail
    @timeit
    def getSourceFileData(self, fileId, fileContent, encoding):
        """
        Parameters:
         - fileId
         - fileContent
         - enum Encoding
        """
        self.__require_access()
        with DBSession(self.__Session) as session:
            sourcefile = session.query(File).get(fileId)

            if sourcefile is None:
                return SourceFileData()

            if fileContent:
                cont = session.query(FileContent).get(sourcefile.content_hash)
                source = zlib.decompress(cont.content)

                if not encoding or encoding == Encoding.DEFAULT:
                    source = codecs.decode(source, 'utf-8', 'replace')
                elif encoding == Encoding.BASE64:
                    source = base64.b64encode(source)

                return SourceFileData(fileId=sourcefile.id,
                                      filePath=sourcefile.filepath,
                                      fileContent=source)
            else:
                return SourceFileData(fileId=sourcefile.id,
                                      filePath=sourcefile.filepath)

    @exc_to_thrift_reqfail
    @timeit
    def getLinesInSourceFileContents(self, lines_in_files_requested, encoding):
        self.__require_access()
        with DBSession(self.__Session) as session:

            res = defaultdict(lambda: defaultdict(str))
            for lines_in_file in lines_in_files_requested:
                sourcefile = session.query(File).get(lines_in_file.fileId)
                cont = session.query(FileContent).get(sourcefile.content_hash)
                lines = zlib.decompress(cont.content).split('\n')
                for line in lines_in_file.lines:
                    content = '' if len(lines) < line else lines[line - 1]
                    if not encoding or encoding == Encoding.DEFAULT:
                        content = codecs.decode(content, 'utf-8', 'replace')
                    elif encoding == Encoding.BASE64:
                        content = base64.b64encode(content)
                    res[lines_in_file.fileId][line] = content

            return res

    def _cmp_helper(self, session, run_ids, report_filter, cmp_data):
        """
        Get the report hashes for all of the runs.
        Return the hash list which should be queried
        in the returned run id list.
        """
        if not run_ids:
            run_ids = ThriftRequestHandler.__get_run_ids_to_query(session,
                                                                  cmp_data)

        base_run_ids = run_ids
        new_run_ids = cmp_data.runIds
        diff_type = cmp_data.diffType

        tag_ids = report_filter.runTag if report_filter else None
        base_line_hashes = get_report_hashes(session,
                                             base_run_ids,
                                             tag_ids)

        # If run tag is set in compare data, after base line hashes are
        # calculated remove it from the report filter because we will filter
        # results by these hashes and there is no need to filter results by
        # these tags again.
        if cmp_data.runTag:
            report_filter.runTag = None

        if not new_run_ids and not cmp_data.runTag:
            return base_line_hashes, base_run_ids

        new_check_hashes = get_report_hashes(session,
                                             new_run_ids,
                                             cmp_data.runTag)

        report_hashes, run_ids = \
            get_diff_hashes_for_query(base_run_ids,
                                      base_line_hashes,
                                      new_run_ids,
                                      new_check_hashes,
                                      diff_type)
        return report_hashes, run_ids

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerCounts(self, run_ids, report_filter, cmp_data, limit,
                         offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = []
        with DBSession(self.__Session) as session:
            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.checker_id).label(
                                      'checker_id'),
                                  func.max(Report.severity).label(
                                      'severity'),
                                  Report.bug_id)
            else:
                q = session.query(Report.checker_id,
                                  Report.severity,
                                  func.count(Report.id))

            q = filter_report_filter(q, filter_expression, run_ids, cmp_data,
                                     diff_hashes)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                unique_checker_q = session.query(q.c.checker_id,
                                                 func.max(q.c.severity),
                                                 func.count(q.c.bug_id)) \
                    .group_by(q.c.checker_id) \
                    .order_by(q.c.checker_id)
            else:
                unique_checker_q = q.group_by(Report.checker_id,
                                              Report.severity) \
                    .order_by(Report.checker_id)

            if limit:
                unique_checker_q = unique_checker_q.limit(limit).offset(offset)

            for name, severity, count in unique_checker_q:
                checker_count = CheckerCount(name=name,
                                             severity=severity,
                                             count=count)
                results.append(checker_count)
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getSeverityCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        with DBSession(self.__Session) as session:
            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.severity).label('severity'),
                                  Report.bug_id)
            else:
                q = session.query(Report.severity,
                                  func.count(Report.id))

            q = filter_report_filter(q, filter_expression, run_ids, cmp_data,
                                     diff_hashes)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                severities = session.query(q.c.severity,
                                           func.count(q.c.bug_id)) \
                    .group_by(q.c.severity)
            else:
                severities = q.group_by(Report.severity)

            results = dict(severities)
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getCheckerMsgCounts(self, run_ids, report_filter, cmp_data, limit,
                            offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        with DBSession(self.__Session) as session:
            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(func.max(Report.checker_message).label(
                                      'checker_message'),
                                  Report.bug_id)
            else:
                q = session.query(Report.checker_message,
                                  func.count(Report.id))

            q = filter_report_filter(q, filter_expression, run_ids, cmp_data,
                                     diff_hashes)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                checker_messages = session.query(q.c.checker_message,
                                                 func.count(q.c.bug_id)) \
                    .group_by(q.c.checker_message) \
                    .order_by(q.c.checker_message)
            else:
                checker_messages = q.group_by(Report.checker_message) \
                                    .order_by(Report.checker_message)

            if limit:
                checker_messages = checker_messages.limit(limit).offset(offset)

            results = dict(checker_messages.all())
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getReviewStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = defaultdict(int)
        with DBSession(self.__Session) as session:
            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            is_unique = report_filter is not None and report_filter.isUnique
            if is_unique:
                q = session.query(Report.bug_id,
                                  func.max(ReviewStatus.status).label(
                                      'status'))
            else:
                q = session.query(func.max(Report.bug_id),
                                  ReviewStatus.status,
                                  func.count(Report.id))

            q = filter_report_filter(q, filter_expression, run_ids, cmp_data,
                                     diff_hashes)

            if is_unique:
                q = q.group_by(Report.bug_id).subquery()
                review_statuses = session.query(func.max(q.c.bug_id),
                                                q.c.status,
                                                func.count(q.c.bug_id)) \
                    .group_by(q.c.status)
            else:
                review_statuses = q.group_by(ReviewStatus.status)

            for _, rev_status, count in review_statuses:
                if rev_status is None:
                    # If no review status is set count it as unreviewed.
                    rev_status = ttypes.ReviewStatus.UNREVIEWED
                    results[rev_status] += count
                else:
                    rev_status = review_status_enum(rev_status)
                    results[rev_status] += count
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getFileCounts(self, run_ids, report_filter, cmp_data, limit, offset):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        with DBSession(self.__Session) as session:
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            stmt = session.query(Report.bug_id,
                                 Report.file_id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .outerjoin(File,
                           File.id == Report.file_id) \
                .filter(filter_expression)

            if run_ids:
                stmt = stmt.filter(Report.run_id.in_(run_ids))

            if report_filter is not None and report_filter.isUnique:
                stmt = stmt.group_by(Report.bug_id, Report.file_id)

            stmt = stmt.subquery()

            # When using pg8000, 1 cannot be passed as parameter to the count
            # function. This is the reason why we have to convert it to
            # Integer (see: https://github.com/mfenniak/pg8000/issues/110)
            count_int = cast(1, sqlalchemy.Integer)
            report_count = session.query(stmt.c.file_id,
                                         func.count(count_int).label(
                                             'report_count')) \
                .group_by(stmt.c.file_id)

            if limit:
                report_count = report_count.limit(limit).offset(offset)

            report_count = report_count.subquery()
            file_paths = session.query(File.filepath,
                                       report_count.c.report_count) \
                .join(report_count,
                      report_count.c.file_id == File.id)

            for fp, count in file_paths:
                results[fp] = count
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getRunHistoryTagCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = []
        with DBSession(self.__Session) as session:
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            tag_run_ids = session.query(RunHistory.run_id.distinct()) \
                .filter(RunHistory.version_tag.isnot(None)) \
                .subquery()

            report_cnt_q = session.query(Report.run_id,
                                         Report.bug_id,
                                         Report.detected_at,
                                         Report.fixed_at) \
                .outerjoin(File, Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \
                .filter(Report.run_id.in_(tag_run_ids)) \
                .subquery()

            is_unique = report_filter is not None and report_filter.isUnique
            count_expr = func.count(report_cnt_q.c.bug_id if not is_unique
                                    else report_cnt_q.c.bug_id.distinct())

            count_q = session.query(RunHistory.id.label('run_history_id'),
                                    count_expr.label('report_count')) \
                .outerjoin(report_cnt_q,
                           report_cnt_q.c.run_id == RunHistory.run_id) \
                .filter(RunHistory.version_tag.isnot(None)) \
                .filter(and_(report_cnt_q.c.detected_at <= RunHistory.time,
                             or_(report_cnt_q.c.fixed_at.is_(None),
                                 report_cnt_q.c.fixed_at >=
                                 RunHistory.time))) \
                .group_by(RunHistory.id) \
                .subquery()

            tag_q = session.query(RunHistory.run_id.label('run_id'),
                                  RunHistory.id.label('run_history_id')) \
                .filter(RunHistory.version_tag.isnot(None))

            if run_ids:
                tag_q = tag_q.filter(RunHistory.run_id.in_(run_ids))

            tag_q = tag_q.subquery()

            q = session.query(tag_q.c.run_history_id,
                              func.max(Run.name).label('run_name'),
                              func.max(RunHistory.id),
                              func.max(RunHistory.time),
                              func.max(RunHistory.version_tag),
                              func.max(count_q.c.report_count)) \
                .outerjoin(RunHistory,
                           RunHistory.id == tag_q.c.run_history_id) \
                .outerjoin(Run, Run.id == tag_q.c.run_id) \
                .outerjoin(count_q,
                           count_q.c.run_history_id == RunHistory.id) \
                .filter(RunHistory.version_tag.isnot(None)) \
                .group_by(tag_q.c.run_history_id, RunHistory.time) \
                .order_by(RunHistory.time.desc())

            for _, run_name, tag_id, version_time, tag, count in q:
                if tag:
                    results.append(RunTagCount(id=tag_id,
                                               time=str(version_time),
                                               name=tag,
                                               runName=run_name,
                                               count=count if count else 0))
        return results

    @exc_to_thrift_reqfail
    @timeit
    def getDetectionStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        with DBSession(self.__Session) as session:
            diff_hashes = None
            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        report_filter,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter(session, report_filter)

            count_expr = func.count(literal_column('*'))

            q = session.query(Report.detection_status,
                              count_expr)

            q = filter_report_filter(q, filter_expression, run_ids, cmp_data,
                                     diff_hashes)

            detection_stats = q.group_by(Report.detection_status).all()

            results = dict(detection_stats)
            results = {detection_status_enum(k): v for k, v in results.items()}

        return results

    # -----------------------------------------------------------------------
    @timeit
    def getPackageVersion(self):
        return self.__package_version

    # -----------------------------------------------------------------------
    @exc_to_thrift_reqfail
    @timeit
    def removeRunResults(self, run_ids):
        self.__require_store()

        failed = False
        for run_id in run_ids:
            try:
                self.removeRun(run_id)
            except Exception as ex:
                LOG.error("Failed to remove run: %s", run_id)
                LOG.error(ex)
                failed = True
        return not failed

    def __removeReports(self, session, report_ids, chunk_size=500):
        """
        Removing reports in chunks.
        """
        for r_ids in [report_ids[i:i + chunk_size] for
                      i in range(0, len(report_ids),
                                 chunk_size)]:
            session.query(Report) \
                .filter(Report.id.in_(r_ids)) \
                .delete(synchronize_session=False)

    @exc_to_thrift_reqfail
    @timeit
    def removeRunReports(self, run_ids, report_filter, cmp_data):
        self.__require_store()

        if not run_ids:
            run_ids = []

        if cmp_data and cmp_data.runIds:
            run_ids.extend(cmp_data.runIds)

        with DBSession(self.__Session) as session:
            check_remove_runs_lock(session, run_ids)

            try:
                diff_hashes = None
                if cmp_data:
                    diff_hashes, _ = self._cmp_helper(session,
                                                      run_ids,
                                                      report_filter,
                                                      cmp_data)
                    if not diff_hashes:
                        # There is no difference.
                        return True

                filter_expression = process_report_filter(session,
                                                          report_filter)

                q = session.query(Report.id) \
                    .outerjoin(File, Report.file_id == File.id) \
                    .outerjoin(ReviewStatus,
                               ReviewStatus.bug_hash == Report.bug_id) \
                    .filter(filter_expression)

                if run_ids:
                    q = q.filter(Report.run_id.in_(run_ids))

                if cmp_data:
                    q = q.filter(Report.bug_id.in_(diff_hashes))

                reports_to_delete = [r[0] for r in q]
                if reports_to_delete:
                    self.__removeReports(session, reports_to_delete)

                # Delete files and contents that are not present
                # in any bug paths.
                db_cleanup.remove_unused_files(session)
                session.commit()
                session.close()
                return True
            except Exception as ex:
                session.rollback()
                LOG.error("Database cleanup failed.")
                LOG.error(ex)
                return False

    @exc_to_thrift_reqfail
    @timeit
    def removeRun(self, run_id):
        self.__require_store()

        # Remove the whole run.
        with DBSession(self.__Session) as session:
            check_remove_runs_lock(session, [run_id])

            session.query(Run) \
                .filter(Run.id == run_id) \
                .delete(synchronize_session=False)

            # Delete files and contents that are not present
            # in any bug paths.
            db_cleanup.remove_unused_files(session)

            session.commit()
            session.close()

            LOG.info("Run '%s' was removed by '%s'.", run_id,
                     self.__get_username())
        return True

    @exc_to_thrift_reqfail
    def getSuppressFile(self):
        """
        Return the suppress file path or empty string if not set.
        """
        self.__require_access()
        suppress_file = self.__src_comment_handler.suppress_file
        if suppress_file:
            return suppress_file
        return ''

    @exc_to_thrift_reqfail
    @timeit
    def addSourceComponent(self, name, value, description):
        """
        Adds a new source if it does not exist or updates an old one.
        """
        self.__require_admin()

        with DBSession(self.__Session) as session:
            component = session.query(SourceComponent).get(name)
            user = self.__auth_session.user if self.__auth_session else None

            if component:
                component.value = value
                component.description = description
                component.user = user
            else:
                component = SourceComponent(name,
                                            value,
                                            description,
                                            user)

            session.add(component)
            session.commit()

            return True

    @exc_to_thrift_reqfail
    @timeit
    def getSourceComponents(self, component_filter):
        """
        Returns the available source components.
        """
        self.__require_access()
        with DBSession(self.__Session) as session:
            q = session.query(SourceComponent)

            if component_filter and component_filter:
                sql_component_filter = [SourceComponent.name.ilike(conv(cf))
                                        for cf in component_filter]
                q = q.filter(*sql_component_filter)

            q = q.order_by(SourceComponent.name)

            return list(map(lambda c:
                            SourceComponentData(c.name,
                                                c.value,
                                                c.description), q))

    @exc_to_thrift_reqfail
    @timeit
    def removeSourceComponent(self, name):
        """
        Removes a source component.
        """
        self.__require_admin()

        with DBSession(self.__Session) as session:
            component = session.query(SourceComponent).get(name)
            if component:
                session.delete(component)
                session.commit()
                LOG.info("Source component '%s' has been removed by '%s'",
                         name, self.__get_username())
                return True
            else:
                msg = 'Source component ' + str(name) + \
                      ' was not found in the database.'
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

    @exc_to_thrift_reqfail
    @timeit
    def getMissingContentHashes(self, file_hashes):
        self.__require_store()

        if not file_hashes:
            return []

        with DBSession(self.__Session) as session:

            q = session.query(FileContent) \
                .options(sqlalchemy.orm.load_only('content_hash')) \
                .filter(FileContent.content_hash.in_(file_hashes))

            return list(set(file_hashes) -
                        set(map(lambda fc: fc.content_hash, q)))

    def __store_source_files(self, source_root, filename_to_hash,
                             trim_path_prefixes):
        """
        Storing file contents from plist.
        """

        file_path_to_id = {}

        for file_name, file_hash in filename_to_hash.items():
            source_file_name = os.path.join(source_root,
                                            file_name.strip("/"))
            source_file_name = os.path.realpath(source_file_name)
            LOG.debug("Storing source file: %s", source_file_name)
            trimmed_file_path = util.trim_path_prefixes(file_name,
                                                        trim_path_prefixes)

            if not os.path.isfile(source_file_name):
                # The file was not in the ZIP file, because we already
                # have the content. Let's check if we already have a file
                # record in the database or we need to add one.

                LOG.debug(file_name + ' not found or already stored.')
                with DBSession(self.__Session) as session:
                    fid = store_handler.addFileRecord(session,
                                                      trimmed_file_path,
                                                      file_hash)
                if not fid:
                    LOG.error("File ID for %s is not found in the DB with "
                              "content hash %s. Missing from ZIP?",
                              source_file_name, file_hash)
                file_path_to_id[file_name] = fid
                LOG.debug("%d fileid found", fid)
                continue

            with codecs.open(source_file_name, 'r',
                             'UTF-8', 'replace') as source_file:
                file_content = source_file.read()
                file_content = codecs.encode(file_content, 'utf-8')

                with DBSession(self.__Session) as session:
                    file_path_to_id[file_name] = \
                        store_handler.addFileContent(session,
                                                     trimmed_file_path,
                                                     file_content,
                                                     file_hash,
                                                     None)
        return file_path_to_id

    def __store_reports(self, session, report_dir, source_root, run_id,
                        file_path_to_id, run_history_time, severity_map,
                        wrong_src_code_comments, skip_handler,
                        checkers):
        """
        Parse up and store the plist report files.
        """

        all_reports = session.query(Report) \
            .filter(Report.run_id == run_id) \
            .all()

        hash_map_reports = defaultdict(list)
        for report in all_reports:
            hash_map_reports[report.bug_id].append(report)

        already_added = set()
        new_bug_hashes = set()

        # Get checker names which was enabled during the analysis.
        enabled_checkers = set()
        disabled_checkers = set()
        for analyzer_checkers in checkers.values():
            if isinstance(analyzer_checkers, dict):
                for checker_name, enabled in analyzer_checkers.iteritems():
                    if enabled:
                        enabled_checkers.add(checker_name)
                    else:
                        disabled_checkers.add(checker_name)
            else:
                enabled_checkers.update(analyzer_checkers)

        def checker_is_unavailable(checker_name):
            """
            Returns True if the given checker is unavailable.

            We filter out checkers which start with 'clang-diagnostic-' because
            these are warnings and the warning list is not available right now.

            FIXME: using the 'diagtool' could be a solution later so the
            client can send the warning list to the server.
            """
            return not checker_name.startswith('clang-diagnostic-') and \
                enabled_checkers and checker_name not in enabled_checkers

        # Processing PList files.
        _, _, report_files = next(os.walk(report_dir), ([], [], []))
        for f in report_files:
            if not f.endswith('.plist'):
                continue

            LOG.debug("Parsing input file '%s'", f)

            try:
                files, reports = plist_parser.parse_plist(
                    os.path.join(report_dir, f), source_root)
            except Exception as ex:
                LOG.error('Parsing the plist failed: %s', str(ex))
                continue

            file_ids = {}
            for file_name in files:
                file_ids[file_name] = file_path_to_id[file_name]

            # Store report.
            for report in reports:
                checker_name = report.main['check_name']

                source_file = files[report.main['location']['file']]
                if skip_handler.should_skip(source_file):
                    continue

                bug_paths, bug_events, bug_extended_data = \
                    store_handler.collect_paths_events(report, file_ids,
                                                       files)
                report_path_hash = get_report_path_hash(report, files)
                if report_path_hash in already_added:
                    LOG.debug('Not storing report. Already added')
                    LOG.debug(report)
                    continue

                LOG.debug("Storing check results to the database.")

                LOG.debug("Storing report")
                bug_id = report.main[
                    'issue_hash_content_of_line_in_context']

                detection_status = 'new'
                detected_at = run_history_time

                if bug_id in hash_map_reports:
                    old_report = hash_map_reports[bug_id][0]
                    old_status = old_report.detection_status
                    detection_status = 'reopened' \
                        if old_status == 'resolved' else 'unresolved'
                    detected_at = old_report.detected_at

                if checker_name in disabled_checkers:
                    detection_status = 'off'
                elif checker_is_unavailable(checker_name):
                    detection_status = 'unavailable'

                report_id = store_handler.addReport(
                    session,
                    run_id,
                    file_ids[source_file],
                    report.main,
                    bug_paths,
                    bug_events,
                    bug_extended_data,
                    detection_status,
                    detected_at,
                    severity_map)

                new_bug_hashes.add(bug_id)
                already_added.add(report_path_hash)

                last_report_event = report.bug_path[-1]
                file_name = files[last_report_event['location']['file']]
                source_file_name = os.path.realpath(
                    os.path.join(source_root, file_name.strip("/")))

                if os.path.isfile(source_file_name):
                    sc_handler = SourceCodeCommentHandler(source_file_name)

                    report_line = last_report_event['location']['line']
                    source_file = os.path.basename(file_name)

                    src_comment_data = sc_handler.filter_source_line_comments(
                        report_line,
                        checker_name)

                    if len(src_comment_data) == 1:
                        status = src_comment_data[0]['status']
                        rw_status = ttypes.ReviewStatus.FALSE_POSITIVE
                        if status == 'confirmed':
                            rw_status = ttypes.ReviewStatus.CONFIRMED
                        elif status == 'intentional':
                            rw_status = ttypes.ReviewStatus.INTENTIONAL

                        self._setReviewStatus(report_id,
                                              rw_status,
                                              src_comment_data[0]['message'],
                                              session)
                    elif len(src_comment_data) > 1:
                        LOG.warning(
                            "Multiple source code comment can be found "
                            "for '%s' checker in '%s' at line %s. "
                            "This bug will not be suppressed!",
                            checker_name, source_file, report_line)

                        wrong_src_code = "{0}|{1}|{2}".format(source_file,
                                                              report_line,
                                                              checker_name)
                        wrong_src_code_comments.append(wrong_src_code)

                LOG.debug("Storing done for report %d", report_id)

        reports_to_delete = set()
        for bug_hash, reports in hash_map_reports.items():
            if bug_hash in new_bug_hashes:
                reports_to_delete.update(map(lambda x: x.id, reports))
            else:
                for report in reports:
                    # We set the fix date of a report only if the report
                    # has not been fixed before.
                    if report.fixed_at:
                        continue

                    checker = report.checker_id
                    if checker in disabled_checkers:
                        report.detection_status = 'off'
                    elif checker_is_unavailable(checker):
                        report.detection_status = 'unavailable'
                    else:
                        report.detection_status = 'resolved'

                    report.fixed_at = run_history_time

        if reports_to_delete:
            self.__removeReports(session, list(reports_to_delete))

    @staticmethod
    @exc_to_thrift_reqfail
    def __store_run_lock(session, name, username):
        """
        Store a RunLock record for the given run name into the database.
        """

        # If the run can be stored, we need to lock it first.
        run_lock = session.query(RunLock) \
            .filter(RunLock.name == name) \
            .with_for_update(nowait=True).one_or_none()

        if not run_lock:
            # If there is no lock record for the given run name, the run
            # is not locked -- create a new lock.
            run_lock = RunLock(name, username)
            session.add(run_lock)
        elif run_lock.has_expired(
                db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE):
            # There can be a lock in the database, which has already
            # expired. In this case, we assume that the previous operation
            # has failed, and thus, we can re-use the already present lock.
            run_lock.touch()
            run_lock.username = username
        else:
            # In case the lock exists and it has not expired, we must
            # consider the run a locked one.
            when = run_lock.when_expires(
                db_cleanup.RUN_LOCK_TIMEOUT_IN_DATABASE)

            username = run_lock.username if run_lock.username is not None \
                else "another user"

            LOG.info("Refusing to store into run '%s' as it is locked by "
                     "%s. Lock will expire at '%s'.", name, username, when)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE,
                "The run named '{0}' is being stored into by {1}. If the "
                "other store operation has failed, this lock will expire "
                "at '{2}'.".format(name, username, when))

        # At any rate, if the lock has been created or updated, commit it
        # into the database.
        try:
            session.commit()
        except (sqlalchemy.exc.IntegrityError,
                sqlalchemy.orm.exc.StaleDataError):
            # The commit of this lock can fail.
            #
            # In case two store ops attempt to lock the same run name at the
            # same time, committing the lock in the transaction that commits
            # later will result in an IntegrityError due to the primary key
            # constraint.
            #
            # In case two store ops attempt to lock the same run name with
            # reuse and one of the operation hangs long enough before COMMIT
            # so that the other operation commits and thus removes the lock
            # record, StaleDataError is raised. In this case, also consider
            # the run locked, as the data changed while the transaction was
            # waiting, as another run wholly completed.

            LOG.info("Run '%s' got locked while current transaction "
                     "tried to acquire a lock. Considering run as locked.",
                     name)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE,
                "The run named '{0}' is being stored into by another "
                "user.".format(name))

    @staticmethod
    @exc_to_thrift_reqfail
    def __free_run_lock(session, name):
        """
        Remove the lock from the database for the given run name.
        """
        # Using with_for_update() here so the database (in case it supports
        # this operation) locks the lock record's row from any other access.
        run_lock = session.query(RunLock) \
            .filter(RunLock.name == name) \
            .with_for_update(nowait=True).one()
        session.delete(run_lock)
        session.commit()

    def __check_run_limit(self, run_name):
        """
        Checks the maximum allowed of uploadable runs for the current product.
        """
        max_run_count = self.__manager.get_max_run_count()

        with DBSession(self.__config_database) as session:
            product = session.query(Product).get(self.__product.id)
            if product.run_limit:
                max_run_count = product.run_limit

        # Session that handles constraints on the run.
        with DBSession(self.__Session) as session:
            if max_run_count:
                LOG.debug("Check the maximum number of allowed "
                          "runs which is %d", max_run_count)

                run = session.query(Run) \
                    .filter(Run.name == run_name) \
                    .one_or_none()

                # If max_run_count is not set in the config file, it will allow
                # the user to upload unlimited runs.

                run_count = session.query(Run.id).count()

                # If we are not updating a run or the run count is reached the
                # limit it will throw an exception.
                if not run and run_count >= max_run_count:
                    remove_run_count = run_count - max_run_count + 1
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.GENERAL,
                        'You reached the maximum number of allowed runs '
                        '({0}/{1})! Please remove at least {2} run(s) before '
                        'you try it again.'.format(run_count,
                                                   max_run_count,
                                                   remove_run_count))

    @exc_to_thrift_reqfail
    @timeit
    def massStoreRun(self, name, tag, version, b64zip, force,
                     trim_path_prefixes):
        self.__require_store()

        user = self.__auth_session.user if self.__auth_session else None

        # Check constraints of the run.
        self.__check_run_limit(name)

        with DBSession(self.__Session) as session:
            ThriftRequestHandler.__store_run_lock(session, name, user)

        wrong_src_code_comments = []
        try:
            with TemporaryDirectory() as zip_dir:
                unzip(b64zip, zip_dir)

                LOG.debug("Using unzipped folder '%s'", zip_dir)

                source_root = os.path.join(zip_dir, 'root')
                report_dir = os.path.join(zip_dir, 'reports')
                metadata_file = os.path.join(report_dir, 'metadata.json')
                skip_file = os.path.join(report_dir, 'skip_file')
                content_hash_file = os.path.join(zip_dir,
                                                 'content_hashes.json')

                skip_handler = skiplist_handler.SkipListHandler()
                if os.path.exists(skip_file):
                    LOG.debug("Pocessing skip file %s", skip_file)
                    try:
                        with open(skip_file) as sf:
                            skip_handler = \
                                skiplist_handler.SkipListHandler(sf.read())
                    except (IOError, OSError) as err:
                        LOG.error("Failed to open skip file")
                        LOG.error(err)

                filename_to_hash = util.load_json_or_empty(content_hash_file,
                                                           {})

                file_path_to_id = self.__store_source_files(source_root,
                                                            filename_to_hash,
                                                            trim_path_prefixes)

                run_history_time = datetime.now()

                check_commands, check_durations, cc_version, statistics, \
                    checkers = store_handler.metadata_info(metadata_file)

                command = ''
                if len(check_commands) == 1:
                    command = ' '.join(check_commands[0])
                elif len(check_commands) > 1:
                    command = "multiple analyze calls: " + \
                              '; '.join([' '.join(com)
                                         for com in check_commands])

                durations = 0
                if check_durations:
                    # Round the duration to seconds.
                    durations = int(sum(check_durations))

                # This session's transaction buffer stores the actual run data
                # into the database.
                with DBSession(self.__Session) as session:
                    # Load the lock record for "FOR UPDATE" so that the
                    # transaction that handles the run's store operations
                    # has a lock on the database row itself.
                    run_lock = session.query(RunLock) \
                        .filter(RunLock.name == name) \
                        .with_for_update(nowait=True).one()

                    # Do not remove this seemingly dummy print, we need to make
                    # sure that the execution of the SQL statement is not
                    # optimised away and the fetched row is not garbage
                    # collected.
                    LOG.debug("Storing into run '%s' locked at '%s'.",
                              name, run_lock.locked_at)

                    # Actual store operation begins here.
                    user_name = self.__get_username()
                    run_id = store_handler.addCheckerRun(session,
                                                         command,
                                                         name,
                                                         tag,
                                                         user_name,
                                                         run_history_time,
                                                         version,
                                                         force,
                                                         cc_version,
                                                         statistics)

                    self.__store_reports(session,
                                         report_dir,
                                         source_root,
                                         run_id,
                                         file_path_to_id,
                                         run_history_time,
                                         self.__context.severity_map,
                                         wrong_src_code_comments,
                                         skip_handler,
                                         checkers)

                    store_handler.setRunDuration(session,
                                                 run_id,
                                                 durations)

                    store_handler.finishCheckerRun(session, run_id)

                    session.commit()

                return run_id
        finally:
            # In any case if the "try" block's execution began, a run lock must
            # exist, which can now be removed, as storage either completed
            # successfully, or failed in a detectable manner.
            # (If the failure is undetectable, the coded grace period expiry
            # of the lock will allow further store operations to the given
            # run name.)
            with DBSession(self.__Session) as session:
                ThriftRequestHandler.__free_run_lock(session, name)

            if wrong_src_code_comments:
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.SOURCE_FILE,
                    "Multiple source code comment can be found with the same "
                    "checker name for same bug!",
                    wrong_src_code_comments)

    @exc_to_thrift_reqfail
    @timeit
    def allowsStoringAnalysisStatistics(self):
        self.__require_store()

        return True if self.__manager.get_analysis_statistics_dir() else False

    @exc_to_thrift_reqfail
    @timeit
    def getAnalysisStatisticsLimits(self):
        self.__require_store()

        cfg = dict()

        # Get the limit of failure zip size.
        failure_zip_size = self.__manager.get_failure_zip_size()
        if failure_zip_size:
            cfg[ttypes.StoreLimitKind.FAILURE_ZIP_SIZE] = failure_zip_size

        # Get the limit of compilation database size.
        compilation_database_size = \
            self.__manager.get_compilation_database_size()
        if compilation_database_size:
            cfg[ttypes.StoreLimitKind.COMPILATION_DATABASE_SIZE] = \
                compilation_database_size

        return cfg

    @exc_to_thrift_reqfail
    @timeit
    def storeAnalysisStatistics(self, run_name, b64zip):
        self.__require_store()

        report_dir_store = self.__manager.get_analysis_statistics_dir()
        if report_dir_store:
            try:
                product_dir = os.path.join(report_dir_store,
                                           self.__product.endpoint)

                # Create report store directory.
                if not os.path.exists(product_dir):
                    os.makedirs(product_dir)

                # Removes and replaces special characters in the run name.
                run_name = slugify(run_name)

                run_zip_file = os.path.join(product_dir, run_name + '.zip')
                with open(run_zip_file, 'w') as run_zip:
                    run_zip.write(zlib.decompress(
                        base64.b64decode(b64zip)))
                return True
            except Exception as ex:
                LOG.error(str(ex))
                return False

        return False
