# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests.
"""

import base64
import codecs
from collections import defaultdict
from datetime import datetime
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import zipfile
import zlib

import sqlalchemy
from sqlalchemy import func

import shared
from codeCheckerDBAccess_v6 import constants, ttypes
from codeCheckerDBAccess_v6.ttypes import *

from libcodechecker import generic_package_context
from libcodechecker import suppress_handler
# TODO: Cross-subpackage import here.
from libcodechecker.analyze import plist_parser
from libcodechecker.analyze import store_handler
from libcodechecker.logger import LoggerFactory
from libcodechecker.profiler import timeit
from libcodechecker.server import permissions
from libcodechecker.server.database.run_db_model import *

LOG = LoggerFactory.get_new_logger('RUN ACCESS HANDLER')


class CountFilter:
    FILE = 0
    CHECKER_MSG = 1
    CHECKER_NAME = 2
    SEVERITY = 3
    REVIEW_STATUS = 4
    DETECTION_STATUS = 5
    RUN_HISTORY_TAG = 6


def conv(text):
    """
    Convert * to % got from clients for the database queries.
    """
    if text is None:
        return '%'
    return text.replace('*', '%')


def process_report_filter_v2(report_filter, count_filter=None):
    """
    Process the new report filter.
    If the count_filter parameter is set it will ignore that field type of
    the report_filter.
    E.g.: If counter_filter is equal with Severity, it will ignore severity
    field values of the report_filter.
    """

    if report_filter is None:
        return text('')

    AND = []
    if report_filter.filepath is not None and count_filter != CountFilter.FILE:
        OR = [File.filepath.ilike(conv(fp))
              for fp in report_filter.filepath]
        AND.append(or_(*OR))

    if report_filter.checkerMsg is not None and \
       count_filter != CountFilter.CHECKER_MSG:
        OR = [Report.checker_message.ilike(conv(cm))
              for cm in report_filter.checkerMsg]
        AND.append(or_(*OR))

    if report_filter.checkerName is not None and \
       count_filter != CountFilter.CHECKER_NAME:
        OR = [Report.checker_id.ilike(conv(cn))
              for cn in report_filter.checkerName]
        AND.append(or_(*OR))

    if report_filter.reportHash is not None:
        AND.append(Report.bug_id.in_(report_filter.reportHash))

    if report_filter.severity is not None and \
       count_filter != CountFilter.SEVERITY:
        AND.append(Report.severity.in_(report_filter.severity))

    if report_filter.detectionStatus is not None and \
       count_filter != CountFilter.DETECTION_STATUS:
        dst = list(map(detection_status_str,
                       report_filter.detectionStatus))
        AND.append(Report.detection_status.in_(dst))

    if report_filter.reviewStatus is not None and \
       count_filter != CountFilter.REVIEW_STATUS:
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
           shared.ttypes.DetectionStatus.RESOLVED in detection_status:
            OR.append(Report.fixed_at >= date)
        else:
            OR.append(Report.detected_at >= date)
        AND.append(or_(*OR))

    if report_filter.fixDate is not None:
        date = datetime.fromtimestamp(report_filter.fixDate)

        OR = []
        if detection_status is not None and len(detection_status) == 1 and \
           shared.ttypes.DetectionStatus.RESOLVED in detection_status:
            OR.append(Report.fixed_at < date)
        else:
            OR.append(Report.detected_at < date)
        AND.append(or_(*OR))

    if report_filter.runHistoryTag is not None and \
       count_filter != CountFilter.RUN_HISTORY_TAG:
        OR = []
        for history_date in report_filter.runHistoryTag:
            date = datetime.strptime(history_date,
                                     '%Y-%m-%d %H:%M:%S.%f')
            OR.append(Report.detected_at <= date)
        AND.append(or_(*OR))

    filter_expr = and_(*AND)
    return filter_expr


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


def get_run_result_query_helper(session, run_ids, report_filter, is_unique,
                                is_count=False):
    filter_expression = process_report_filter_v2(report_filter)

    if is_unique:
        q = session.query(Report.bug_id,
                          Report.checker_id,
                          Report.checker_message,
                          Report.severity,
                          File.filename,
                          ReviewStatus) \
            .distinct(Report.bug_id,
                      Report.checker_id,
                      Report.checker_message,
                      Report.severity,
                      File.filename,
                      ReviewStatus.status)
    elif is_count:
        q = session.query(Report)
    else:
        q = session.query(Report,
                          File,
                          ReviewStatus)

    q = q.filter(Report.run_id.in_(run_ids)) \
        .outerjoin(File, Report.file_id == File.id) \
        .outerjoin(ReviewStatus,
                   ReviewStatus.bug_hash == Report.bug_id) \
        .filter(filter_expression)

    return q


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


def detection_status_enum(status):
    if status == 'new':
        return DetectionStatus.NEW
    elif status == 'resolved':
        return DetectionStatus.RESOLVED
    elif status == 'unresolved':
        return DetectionStatus.UNRESOLVED
    elif status == 'reopened':
        return DetectionStatus.REOPENED


def detection_status_str(status):
    if status == DetectionStatus.NEW:
        return 'new'
    elif status == DetectionStatus.RESOLVED:
        return 'resolved'
    elif status == DetectionStatus.UNRESOLVED:
        return 'unresolved'
    elif status == DetectionStatus.REOPENED:
        return 'reopened'


def review_status_str(status):
    if status == ttypes.ReviewStatus.UNREVIEWED:
        return 'unreviewed'
    elif status == ttypes.ReviewStatus.CONFIRMED:
        return 'confirmed'
    elif status == ttypes.ReviewStatus.FALSE_POSITIVE:
        return 'false_positive'
    elif status == ttypes.ReviewStatus.INTENTIONAL:
        return 'intentional'


def review_status_enum(status):
    if status == 'unreviewed':
        return ttypes.ReviewStatus.UNREVIEWED
    elif status == 'confirmed':
        return ttypes.ReviewStatus.CONFIRMED
    elif status == 'false_positive':
        return ttypes.ReviewStatus.FALSE_POSITIVE
    elif status == 'intentional':
        return ttypes.ReviewStatus.INTENTIONAL


def unzip(b64zip):
    """
    This function unzips the base64 encoded zip file. This zip is extracted
    to a temporary directory and the ZIP is then deleted. The function returns
    the name of the extracted directory.
    """

    _, zip_file = tempfile.mkstemp('.zip')
    temp_dir = tempfile.mkdtemp()
    LOG.debug("Unzipping mass storage ZIP '{0}' to '{1}'..."
              .format(zip_file, temp_dir))

    with open(zip_file, 'wb') as zip_f:
        zip_f.write(zlib.decompress(base64.b64decode(b64zip)))

    with zipfile.ZipFile(zip_file, 'r', allowZip64=True) as zipf:
        try:
            zipf.extractall(temp_dir)
        except:
            LOG.error("Failed to extract received ZIP.")
            import traceback
            traceback.print_exc()
            raise

    os.remove(zip_file)
    return temp_dir


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


class StorageSession:
    """
    This class is a singleton which helps to handle a transaction which
    belong to the checking of an entire run. This class holds the SQLAlchemy
    session for the run being checked and the set of touched reports. This
    latter one is needed so at the end the detection status of the rest reports
    can be set to "resolved".
    """

    class __StorageSession:
        def __init__(self):
            self.__sessions = dict()
            self._timeout_sessions()

        def start_run_session(self, run_id, transaction):
            self.__sessions[run_id] = {
                'touched_reports': set(),
                'transaction': transaction,
                'timer': time.time()}

        def end_run_session(self, run_id, run_history_time):
            this_session = self.__sessions[run_id]
            transaction = this_session['transaction']

            # Set resolved reports

            transaction.query(Report) \
                .filter(Report.run_id == run_id,
                        Report.id.notin_(this_session['touched_reports'])) \
                .update({Report.detection_status: 'resolved',
                         Report.fixed_at: run_history_time},
                        synchronize_session='fetch')

            transaction.commit()
            transaction.close()

            del self.__sessions[run_id]

        def abort_session(self, run_id):
            transaction = self.__sessions[run_id]['transaction']
            transaction.rollback()
            transaction.close()
            del self.__sessions[run_id]

        def touch_report(self, run_id, report_id):
            self.__sessions[run_id]['touched_reports'].add(report_id)

        def is_touched(self, run_id, report_id):
            return report_id in self.__sessions[run_id]['touched_reports']

        def has_ongoing_run(self, run_id):
            return run_id in self.__sessions

        def get_transaction(self, run_id):
            self.__sessions[run_id]['timer'] = time.time()
            return self.__sessions[run_id]['transaction']

        # FIXME: do we need this guard at all?
        # Storage is performed locally on the server
        # so why would it timeout?
        def _timeout_sessions(self):
            """
            The storage session times out if no action happens in the
            transaction belonging to the given run within 10 seconds.
            """
            for run_id, session in self.__sessions.iteritems():
                if int(time.time() - session['timer']) > 10:
                    LOG.info('Session timeout for run ' + str(run_id))
                    self.abort_session(run_id)
                    break

            threading.Timer(10, self._timeout_sessions).start()

    instance = None

    def __init__(self):
        if not StorageSession.instance:
            StorageSession.instance = \
                StorageSession.__StorageSession()

    def __getattr__(self, name):
        return getattr(self.instance, name)


class ThriftRequestHandler(object):
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 Session,
                 product,
                 auth_session,
                 config_database,
                 checker_md_docs,
                 checker_md_docs_map,
                 suppress_handler,
                 package_version):

        if not product:
            raise ValueError("Cannot initialize request handler without "
                             "a product to serve.")

        self.__product = product
        self.__auth_session = auth_session
        self.__config_database = config_database
        self.__checker_md_docs = checker_md_docs
        self.__checker_doc_map = checker_md_docs_map
        self.__suppress_handler = suppress_handler
        self.__package_version = package_version
        self.__Session = Session
        self.__storage_session = StorageSession()

        self.__permission_args = {
            'productID': product.id
        }

    def __require_permission(self, required):
        """
        Helper method to raise an UNAUTHORIZED exception if the user does not
        have any of the given permissions.
        """

        try:
            session = self.__config_database()
            args = dict(self.__permission_args)
            args['config_db_session'] = session

            if not any([permissions.require_permission(
                            perm, args, self.__auth_session)
                        for perm in required]):
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.UNAUTHORIZED,
                    "You are not authorized to execute this action.")

            return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    def __require_access(self):
        self.__require_permission([permissions.PRODUCT_ACCESS])

    def __require_store(self):
        self.__require_permission([permissions.PRODUCT_STORE])

    def __sortResultsQuery(self, query, sort_types=None, is_unique=False):
        """
        Helper method for __queryDiffResults and queryResults to apply sorting.
        """

        # Get a list of sort_types which will be a nested ORDER BY.
        sort_type_map = {SortType.FILENAME: [File.filepath],
                         SortType.CHECKER_NAME: [Report.checker_id],
                         SortType.SEVERITY: [Report.severity],
                         SortType.REVIEW_STATUS: [ReviewStatus.status],
                         SortType.DETECTION_STATUS: [Report.detection_status]}

        if is_unique:
            sort_type_map[SortType.FILENAME] = [File.filename]
            sort_type_map[SortType.DETECTION_STATUS] = []

        # Mapping the SQLAlchemy functions.
        order_type_map = {Order.ASC: asc, Order.DESC: desc}

        if sort_types is None:
            sort_types = [SortMode(SortType.SEVERITY, Order.DESC)]

        for sort in sort_types:
            sorttypes = sort_type_map.get(sort.type)
            for sorttype in sorttypes:
                order_type = order_type_map.get(sort.ord)
                query = query.order_by(order_type(sorttype))

        return query

    def __get_run_ids_to_query(self, session, cmp_data=None):
        """
        Return run id list for the queries.
        If compare data is set remove those run ids from the returned list.
        The returned run id list can be used as a baseline for comparisons.
        """
        res = session.query(Run.id).all()
        run_ids = [r[0] for r in res]
        if cmp_data:
            all_rids = set(run_ids)
            cmp_rids = set(cmp_data.runIds)
            run_ids = list(all_rids.difference(cmp_rids))

        return run_ids

    @timeit
    def getRunData(self, run_filter):
        self.__require_access()
        try:
            session = self.__Session()

            # Count the reports subquery.
            stmt = session.query(Report.run_id,
                                 func.count(literal_column('*')).label(
                                     'report_count')) \
                .group_by(Report.run_id) \
                .subquery()

            tag_q = session.query(RunHistory.run_id,
                                  func.max(RunHistory.id).label(
                                      'run_history_id'),
                                  func.max(RunHistory.time).label(
                                      'run_history_time')) \
                .filter(RunHistory.version_tag.isnot(None)) \
                .group_by(RunHistory.run_id) \
                .subquery()

            q = session.query(Run,
                              RunHistory.version_tag,
                              stmt.c.report_count)

            if run_filter is not None:
                if run_filter.ids is not None:
                    q = q.filter(Run.id.in_(run_filter.ids))
                if run_filter.names is not None:
                    if run_filter.exactMatch:
                        q = q.filter(Run.name.in_(run_filter.names))
                    else:
                        OR = [Run.name.ilike('%' + name + '%') for
                              name in run_filter.names]
                        q = q.filter(or_(*OR))

            q = q.outerjoin(stmt, Run.id == stmt.c.run_id) \
                .outerjoin(tag_q, Run.id == tag_q.c.run_id) \
                .outerjoin(RunHistory,
                           RunHistory.id == tag_q.c.run_history_id) \
                .group_by(Run.id,
                          RunHistory.version_tag,
                          stmt.c.report_count) \
                .order_by(Run.date)

            status_q = session.query(Report.run_id,
                                     Report.detection_status,
                                     func.count(literal_column('*'))
                                         .label('status_count')) \
                .group_by(Report.run_id, Report.detection_status)

            status_sum = defaultdict(defaultdict)
            for run_id, status, count in status_q:
                status_sum[run_id][detection_status_enum(status)] = count

            results = []

            for instance, version_tag, reportCount in q:
                if reportCount is None:
                    reportCount = 0

                results.append(RunData(instance.id,
                                       str(instance.date),
                                       instance.name,
                                       instance.duration,
                                       reportCount,
                                       instance.command,
                                       status_sum[instance.id],
                                       version_tag))
            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getRunHistory(self, run_ids, limit, offset):
        self.__require_access()
        try:
            session = self.__Session()

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, None)

            res = session.query(RunHistory) \
                .filter(RunHistory.run_id.in_(run_ids)) \
                .order_by(RunHistory.time.desc()) \
                .limit(limit) \
                .offset(offset)

            results = []
            for history in res:
                results.append(RunHistoryData(runId=history.run.id,
                                              runName=history.run.name,
                                              versionTag=history.version_tag,
                                              user=history.user,
                                              time=str(history.time)))

            return results
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getReport(self, reportId):
        self.__require_access()
        try:
            session = self.__Session()

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
                detectionStatus=detection_status_enum(report.detection_status))
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE,
                msg)
        finally:
            session.close()

    @timeit
    def getRunResults(self, run_ids, limit, offset, sort_types,
                      report_filter, cmp_data):
        self.__require_access()
        max_query_limit = constants.MAX_QUERY_SIZE
        if limit > max_query_limit:
            LOG.debug('Query limit ' + str(limit) +
                      ' was larger than max query limit ' +
                      str(max_query_limit) + ', setting limit to ' +
                      str(max_query_limit))
            limit = max_query_limit

        session = self.__Session()

        try:

            results = []

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            is_unique = report_filter is not None and report_filter.isUnique
            q = get_run_result_query_helper(session, run_ids, report_filter,
                                            is_unique)

            q = self.__sortResultsQuery(q, sort_types, is_unique)

            # This is needed to resolved pgsql DISTINCT expressions must match
            # initial ORDER BY expressions problem.
            if is_unique:
                q = q.order_by(Report.bug_id,
                               Report.checker_id,
                               Report.checker_message,
                               Report.severity,
                               File.filename,
                               ReviewStatus.status)

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            if is_unique:
                for report_hash, checker, checker_msg, severity,\
                    path, review_status in \
                        q.limit(limit).offset(offset):

                    review_data = create_review_data(review_status)
                    results.append(
                        ReportData(bugHash=report_hash,
                                   checkedFile=path,
                                   checkerMsg=checker_msg,
                                   checkerId=checker,
                                   severity=severity,
                                   reviewData=review_data)
                    )
            else:
                for report, source_file, review_status in \
                        q.limit(limit).offset(offset):

                    review_data = create_review_data(review_status)
                    results.append(
                        ReportData(runId=report.run_id,
                                   bugHash=report.bug_id,
                                   checkedFile=source_file.filepath,
                                   checkerMsg=report.checker_message,
                                   reportId=report.id,
                                   fileId=source_file.id,
                                   line=report.line,
                                   column=report.column,
                                   checkerId=report.checker_id,
                                   severity=report.severity,
                                   reviewData=review_data,
                                   detectionStatus=detection_status_enum(
                                       report.detection_status))
                    )

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    @timeit
    def getRunReportCounts(self, run_ids, report_filter):
        """
          Count the results separately for multiple runs.
          If an empty run id list is provided the report
          counts will be calculated for all of the available runs.
        """
        self.__require_access()
        results = []
        session = self.__Session()
        try:
            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session)

            filter_expression = process_report_filter_v2(report_filter)

            count_expr = func.count(literal_column('*'))

            q = session.query(func.max(Report.id), Run, count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File, Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .outerjoin(Run,
                           Report.run_id == Run.id) \
                .filter(filter_expression).group_by(Run.id).all()

            for _, run, count in q:
                report_count = RunReportCount(runId=run.id,
                                              name=run.name,
                                              reportCount=count)
                results.append(report_count)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()
            return results

    @timeit
    def getRunResultCount(self, run_ids, report_filter, cmp_data):
        self.__require_access()
        session = self.__Session()

        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return 0

            is_unique = report_filter is not None and report_filter.isUnique
            q = get_run_result_query_helper(session, run_ids, report_filter,
                                            is_unique, True)

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            reportCount = q.count()

            if reportCount is None:
                reportCount = 0

            return reportCount

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        finally:
            session.close()

    @timeit
    def __construct_bug_item_list(self, session, report_id, item_type):

        q = session.query(item_type) \
            .filter(item_type.report_id == report_id) \
            .order_by(item_type.order)

        bug_items = []

        for event in q:
            f = session.query(File).get(event.file_id)
            bug_items.append((event, f.filepath))

        return bug_items

    @timeit
    def getReportDetails(self, reportId):
        """
        Parameters:
         - reportId
        """
        self.__require_access()
        try:
            session = self.__Session()

            report = session.query(Report).get(reportId)

            events = self.__construct_bug_item_list(session,
                                                    report.id,
                                                    BugPathEvent)
            bug_events_list = []
            for event, file_path in events:
                event = bugpathevent_db_to_api(event)
                event.filePath = file_path
                bug_events_list.append(event)

            points = self.__construct_bug_item_list(session,
                                                    report.id,
                                                    BugReportPoint)

            bug_point_list = []
            for bug_point, file_path in points:
                bug_point = bugreportpoint_db_to_api(bug_point)
                bug_point.filePath = file_path
                bug_point_list.append(bug_point)

            return ReportDetails(bug_events_list, bug_point_list)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    def _setReviewStatus(self, report_id, status, message, session):
        """
        This function sets the review status of the given report. This is the
        implementation of changeReviewStatus(), but it is also extended with
        a session parameter which represents a database transaction. This is
        needed because during storage a specific session object has to be used.
        """
        self.__require_permission([permissions.PRODUCT_ACCESS,
                                   permissions.PRODUCT_STORE])
        try:
            report = session.query(Report).get(report_id)
            if report:
                review_status = session.query(ReviewStatus).get(report.bug_id)
                if review_status is None:
                    review_status = ReviewStatus()
                    review_status.bug_hash = report.bug_id

                user = self.__auth_session.user \
                    if self.__auth_session else "Anonymous"

                review_status.status = review_status_str(status)
                review_status.author = user
                review_status.message = message
                review_status.date = datetime.now()

                session.add(review_status)
                session.flush()

                return True
            else:
                msg = 'Report id ' + str(report_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE, msg)

    @timeit
    def changeReviewStatus(self, report_id, status, message):
        """
        Change review status of the bug by report id.
        """
        try:
            session = self.__Session()
            res = self._setReviewStatus(report_id, status, message, session)
            session.commit()
        finally:
            session.close()

        return res

    @timeit
    def getComments(self, report_id):
        """
            Return the list of comments for the given bug.
        """
        self.__require_access()
        try:
            session = self.__Session()
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
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)
        finally:
            session.close()

    @timeit
    def getCommentCount(self, report_id):
        """
            Return the number of comments for the given bug.
        """
        self.__require_access()
        try:
            session = self.__Session()
            report = session.query(Report).get(report_id)
            if report:
                commentCount = session.query(Comment) \
                    .filter(Comment.bug_hash == report.bug_id) \
                    .count()

            if commentCount is None:
                commentCount = 0

            return commentCount
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)
        finally:
            session.close()

    @timeit
    def addComment(self, report_id, comment_data):
        """
            Add new comment for the given bug.
        """
        self.__require_access()
        session = self.__Session()
        try:
            report = session.query(Report).get(report_id)
            if report:
                user = self.__auth_session.user\
                    if self.__auth_session else "Anonymous"
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
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)
        finally:
            session.close()

    @timeit
    def updateComment(self, comment_id, content):
        """
            Update the given comment message with new content. We allow
            comments to be updated by it's original author only, except for
            Anyonymous comments that can be updated by anybody.
        """
        self.__require_access()
        try:
            session = self.__Session()

            user = self.__auth_session.user \
                if self.__auth_session else "Anonymous"

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
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)
        finally:
            session.close()

    @timeit
    def removeComment(self, comment_id):
        """
            Remove the comment. We allow comments to be removed by it's
            original author only, except for Anyonymous comments that can be
            updated by anybody.
        """
        self.__require_access()
        try:
            session = self.__Session()

            user = self.__auth_session.user \
                if self.__auth_session else "Anonymous"

            comment = session.query(Comment).get(comment_id)
            if comment:
                if comment.author != 'Anonymous' and comment.author != user:
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.UNAUTHORIZED,
                        'Unathorized comment modification!')
                session.delete(comment)
                session.commit()
                return True
            else:
                msg = 'Comment id ' + str(comment_id) + \
                      ' was not found in the database.'
                LOG.error(msg)
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE, msg)
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)
        finally:
            session.close()

    def getCheckerDoc(self, checkerId):
        """
        Parameters:
         - checkerId
        """

        text = "No documentation found for checker: " + checkerId + \
               "\n\nPlease refer to the documentation at the "
        sa_link = "http://clang-analyzer.llvm.org/available_checks.html"
        tidy_link = "http://clang.llvm.org/extra/clang-tidy/checks/list.html"

        if "." in checkerId:
            text += "[ClangSA](" + sa_link + ")"
        elif "-" in checkerId:
            text += "[ClangTidy](" + tidy_link + ")"
        text += " homepage."

        try:
            md_file = self.__checker_doc_map.get(checkerId)
            if md_file:
                md_file = os.path.join(self.__checker_md_docs, md_file)
                with open(md_file, 'r') as md_content:
                    text = md_content.read()

            return text

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              msg)

    @timeit
    def getSourceFileData(self, fileId, fileContent, encoding):
        """
        Parameters:
         - fileId
         - fileContent
         - enum Encoding
        """
        self.__require_access()
        try:
            session = self.__Session()
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

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)
        finally:
            session.close()

    def _cmp_helper(self, session, run_ids, cmp_data):
        """
        Get the report hashes for all of the runs.
        Return the hash list which should be queried
        in the returned run id list.
        """
        base_run_ids = run_ids
        new_run_ids = cmp_data.runIds
        diff_type = cmp_data.diffType

        base_line_hashes = self.__get_hashes_for_runs(session, base_run_ids)

        if not new_run_ids:
            return base_line_hashes, base_run_ids

        new_check_hashes = self.__get_hashes_for_runs(session, new_run_ids)

        report_hashes, run_ids = \
            get_diff_hashes_for_query(base_run_ids,
                                      base_line_hashes,
                                      new_run_ids,
                                      new_check_hashes,
                                      diff_type)
        return report_hashes, run_ids

    @timeit
    def getCheckerCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = []
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(
                report_filter, CountFilter.CHECKER_NAME)

            count_expr = create_count_expression(report_filter)

            q = session.query(Report.checker_id,
                              Report.severity,
                              count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            q = q.group_by(Report.checker_id, Report.severity).all()

            for name, severity, count in q:
                checker_count = CheckerCount(name=name,
                                             severity=severity,
                                             count=count)
                results.append(checker_count)

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def getSeverityCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(report_filter,
                                                         CountFilter.SEVERITY)

            count_expr = create_count_expression(report_filter)

            q = session.query(Report.severity, count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            checker_ids = q.group_by(Report.severity).all()

            results = dict(checker_ids)

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def getCheckerMsgCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(
                report_filter, CountFilter.CHECKER_MSG)

            count_expr = create_count_expression(report_filter)

            q = session.query(Report.checker_message, count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            checker_ids = q.group_by(Report.checker_message).all()

            results = dict(checker_ids)

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def getReviewStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = defaultdict(int)
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(
                report_filter, CountFilter.REVIEW_STATUS)

            count_expr = create_count_expression(report_filter)

            q = session.query(func.max(Report.id),
                              ReviewStatus.status,
                              count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            review_statuses = q.group_by(ReviewStatus.status).all()

            for _, rev_status, count in review_statuses:
                if rev_status is None:
                    # If no review status is set count it as unreviewed.
                    rev_status = ttypes.ReviewStatus.UNREVIEWED
                    results[rev_status] += count
                else:
                    rev_status = review_status_enum(rev_status)
                    results[rev_status] += count

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def getFileCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(report_filter,
                                                         CountFilter.FILE)

            count_expr = create_count_expression(report_filter)

            q = session.query(func.max(Report.id),
                              File.filepath,
                              count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            file_paths = q.group_by(File.filepath).all()

            for _, fp, count in file_paths:
                results[fp] = count

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def getRunHistoryTagCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = []
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(
                report_filter, CountFilter.RUN_HISTORY_TAG)

            count_expr = create_count_expression(report_filter)

            q = session.query(func.max(Report.id),
                              Run.name,
                              RunHistory.time,
                              RunHistory.version_tag,
                              count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(Run,
                           Run.id == Report.run_id) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(RunHistory,
                           RunHistory.run_id == Report.run_id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            history_tags = q.group_by(Run.name,
                                      RunHistory.time,
                                      RunHistory.version_tag).all()

            for _, run_name, time, tag, count in history_tags:
                if tag:
                    results.append(RunTagCount(time=str(time),
                                               name=run_name + ':' + tag,
                                               count=count))

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def getDetectionStatusCounts(self, run_ids, report_filter, cmp_data):
        """
          If the run id list is empty the metrics will be counted
          for all of the runs and in compare mode all of the runs
          will be used as a baseline excluding the runs in compare data.
        """
        self.__require_access()
        results = {}
        session = self.__Session()
        try:

            if not run_ids:
                run_ids = self.__get_run_ids_to_query(session, cmp_data)

            if cmp_data:
                diff_hashes, run_ids = self._cmp_helper(session,
                                                        run_ids,
                                                        cmp_data)
                if not diff_hashes:
                    # There is no difference.
                    return results

            filter_expression = process_report_filter_v2(
                report_filter, CountFilter.DETECTION_STATUS)

            count_expr = func.count(literal_column('*'))

            q = session.query(Report.detection_status,
                              count_expr) \
                .filter(Report.run_id.in_(run_ids)) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression) \

            if cmp_data:
                q = q.filter(Report.bug_id.in_(diff_hashes))

            detection_stats = q.group_by(Report.detection_status).all()

            results = dict(detection_stats)
            results = {detection_status_enum(k): v for k, v in results.items()}

        except Exception as ex:
            LOG.error(ex)
        finally:
            session.close()
            return results

    @timeit
    def __get_hashes_for_runs(self, session, run_ids):

        LOG.debug('query all hashes')
        # Keyed tuple list is returned.
        base_line_hashes = session.query(Report.bug_id) \
            .filter(Report.run_id.in_(run_ids)) \
            .all()

        return set([t[0] for t in base_line_hashes])

    # -----------------------------------------------------------------------
    @timeit
    def getPackageVersion(self):
        return self.__package_version

    # -----------------------------------------------------------------------
    @timeit
    def removeRunResults(self, run_ids):
        self.__require_store()
        session = self.__Session()

        runs_to_delete = []
        for run_id in run_ids:
            LOG.debug('Run id to delete: ' + str(run_id))

            run_to_delete = session.query(Run).get(run_id)
            if not run_to_delete.can_delete:
                LOG.debug("Can't delete " + str(run_id))
                continue

            run_to_delete.can_delete = False
            session.commit()
            runs_to_delete.append(run_to_delete)

        for run_to_delete in runs_to_delete:
            # FIXME: clean up bugpaths. Once run_id is a foreign key there,
            # it should be automatic.
            session.delete(run_to_delete)
            session.commit()

        # Delete files and contents that are not present in any bug paths.
        s1 = select([BugPathEvent.file_id])
        s2 = select([BugReportPoint.file_id])
        session.query(File).filter(not_(File.id.in_(s1.union(s2)))).delete(
            synchronize_session=False)
        session.query(FileContent).filter(not_(FileContent.content_hash.in_(
            select([File.content_hash])))).delete(synchronize_session=False)
        session.commit()
        session.close()
        return True

    # -----------------------------------------------------------------------
    def getSuppressFile(self):
        """
        Return the suppress file path or empty string if not set.
        """
        self.__require_access()
        suppress_file = self.__suppress_handler.suppress_file
        if suppress_file:
            return suppress_file
        return ''

    @timeit
    def getMissingContentHashes(self, file_hashes):
        self.__require_store()
        try:
            session = self.__Session()

            q = session.query(FileContent) \
                .options(sqlalchemy.orm.load_only('content_hash')) \
                .filter(FileContent.content_hash.in_(file_hashes))

            return list(set(file_hashes) -
                        set(map(lambda fc: fc.content_hash, q)))

        finally:
            session.close()

    @timeit
    def massStoreRun(self, name, tag, version, b64zip, force):
        self.__require_store()

        try:
            session = self.__Session()
            run = session.query(Run).filter(Run.name == name).one_or_none()

            if run and self.__storage_session.has_ongoing_run(run.id):
                raise Exception('Storage of ' + name + ' is already going!')
        finally:
            session.close()

        # Unzip sent data.
        zip_dir = unzip(b64zip)

        LOG.debug("Using unzipped folder '{0}'".format(zip_dir))

        source_root = os.path.join(zip_dir, 'root')
        report_dir = os.path.join(zip_dir, 'reports')
        metadata_file = os.path.join(report_dir, 'metadata.json')
        content_hash_file = os.path.join(zip_dir, 'content_hashes.json')

        with open(content_hash_file) as chash_file:
            filename2hash = json.load(chash_file)

        check_commands, check_durations = \
            store_handler.metadata_info(metadata_file)

        if len(check_commands) == 0:
            command = ' '.join(sys.argv)
        elif len(check_commands) == 1:
            command = ' '.join(check_commands[0])
        else:
            command = "multiple analyze calls: " + \
                      '; '.join([' '.join(com) for com in check_commands])

        # Storing file contents from plist.
        file_path_to_id = {}

        for file_name, file_hash in filename2hash.items():
            source_file_name = os.path.join(source_root,
                                            file_name.strip("/"))
            source_file_name = os.path.realpath(source_file_name)
            LOG.debug("Storing source file: " + source_file_name)

            if not os.path.isfile(source_file_name):
                # The file was not in the ZIP file, because we already have the
                # content. Let's check if we already have a file record in the
                # database or we need to add one.

                LOG.debug(file_name + ' not found or already stored.')
                fid = store_handler.addFileRecord(self.__Session(),
                                                  file_name,
                                                  file_hash)
                if not fid:
                    LOG.error("File ID for " + source_file_name +
                              " is not found in the DB with content hash " +
                              file_hash +
                              ". Missing from ZIP?")
                file_path_to_id[file_name] = fid
                LOG.debug(str(fid) + " fileid found")
                continue

            with codecs.open(source_file_name, 'r',
                             'UTF-8', 'replace') as source_file:
                file_content = source_file.read()
                file_content = codecs.encode(file_content, 'utf-8')

                file_path_to_id[file_name] = \
                    store_handler.addFileContent(self.__Session(),
                                                 file_name,
                                                 file_content,
                                                 file_hash,
                                                 None)

        user = self.__auth_session.user \
            if self.__auth_session else 'Anonymous'

        run_history_time = datetime.now()
        run_id = store_handler.addCheckerRun(self.__Session(),
                                             self.__storage_session,
                                             command,
                                             name,
                                             tag,
                                             user,
                                             run_history_time,
                                             version,
                                             force)

        session = self.__storage_session.get_transaction(run_id)

        # Processing PList files.
        _, _, report_files = next(os.walk(report_dir), ([], [], []))
        for f in report_files:
            if not f.endswith('.plist'):
                continue

            LOG.debug("Parsing input file '" + f + "'")

            try:
                # FIXME: We are parsing the plists for the
                # second time here. Use re-use the
                # previous results.
                files, reports = plist_parser.parse_plist(
                    os.path.join(report_dir, f))
            except Exception as ex:
                LOG.error('Parsing the plist failed: ' + str(ex))
                continue

            file_ids = {}
            # Store content of file to the server if needed.
            for file_name in files:
                file_ids[file_name] = file_path_to_id[file_name]

            # Store report.
            for report in reports:
                LOG.debug("Storing check results to the database.")

                checker_name = report.main['check_name']
                context = generic_package_context.get_context()
                severity_name = context.severity_map.get(checker_name,
                                                         'UNSPECIFIED')
                severity = \
                    Severity._NAMES_TO_VALUES[severity_name]

                bug_paths, bug_events = \
                    store_handler.collect_paths_events(report, file_ids, files)

                LOG.debug("Storing report")
                report_id = store_handler.addReport(
                    self.__storage_session,
                    run_id,
                    file_ids[files[report.main['location']['file']]],
                    report.main,
                    bug_paths,
                    bug_events,
                    checker_name,
                    severity,
                    run_history_time)

                last_report_event = report.bug_path[-1]
                sp_handler = suppress_handler.SourceSuppressHandler(
                    files[last_report_event['location']['file']],
                    last_report_event['location']['line'],
                    report.main['issue_hash_content_of_line_in_context'],
                    report.main['check_name'])

                supp = sp_handler.get_suppressed()
                if supp:
                    _, _, comment = supp
                    status = ttypes.ReviewStatus.FALSE_POSITIVE
                    self._setReviewStatus(report_id, status, comment, session)

                LOG.debug("Storing done for report " + str(report_id))

        if len(check_durations) > 0:
            store_handler.setRunDuration(self.__storage_session,
                                         run_id,
                                         # Round the duration to seconds.
                                         int(sum(check_durations)))

        store_handler.finishCheckerRun(self.__storage_session, run_id,
                                       run_history_time)

        # TODO: This directory should be removed even if an exception is thrown
        # above.
        shutil.rmtree(zip_dir)

        return run_id
