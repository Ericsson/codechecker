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
import datetime
import os
import zlib

import sqlalchemy

import shared
from codeCheckerDBAccess import constants
from codeCheckerDBAccess.ttypes import *

from libcodechecker.logger import LoggerFactory
from libcodechecker.orm_model import *
from libcodechecker.profiler import timeit

LOG = LoggerFactory.get_new_logger('ACCESS HANDLER')


def conv(text):
    """
    Convert * to % got from clients for the database queries.
    """
    if text is None:
        return '%'
    return text.replace('*', '%')


def construct_report_filter(report_filters):
    """
    Construct the report filter for reports and suppressed reports.
    """

    OR = []
    if report_filters is None:
        AND = [Report.checker_message.like('%'), Report.checker_id.like('%'),
               File.filepath.like('%')]

        OR.append(and_(*AND))
        filter_expression = or_(*OR)
        return filter_expression

    for report_filter in report_filters:
        AND = []
        if report_filter.checkerMsg:
            AND.append(Report.checker_message.ilike(
                conv(report_filter.checkerMsg)))
        if report_filter.checkerId:
            AND.append(Report.checker_id.ilike(
                conv(report_filter.checkerId)))
        if report_filter.filepath:
            AND.append(File.filepath.ilike(
                conv(report_filter.filepath)))
        if report_filter.severity is not None:
            # severity value can be 0
            AND.append(Report.severity == report_filter.severity)
        if report_filter.bugHash:
            AND.append(Report.bug_id == report_filter.bugHash)

        OR.append(and_(*AND))

    filter_expression = or_(*OR)

    return filter_expression


def bugpathevent_db_to_api(bpe):
    return shared.ttypes.BugPathEvent(
        startLine=bpe.line_begin,
        startCol=bpe.col_begin,
        endLine=bpe.line_end,
        endCol=bpe.col_end,
        msg=bpe.msg,
        fileId=bpe.file_id)


def bugreportpoint_db_to_api(brp):
    return shared.ttypes.BugPathPos(
        startLine=brp.line_begin,
        startCol=brp.col_begin,
        endLine=brp.line_end,
        endCol=brp.col_end,
        fileId=brp.file_id)


class ThriftRequestHandler(object):
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 session,
                 auth_session,
                 checker_md_docs,
                 checker_md_docs_map,
                 suppress_handler,
                 db_version_info,
                 package_version):

        self.__auth_session = auth_session
        self.__checker_md_docs = checker_md_docs
        self.__checker_doc_map = checker_md_docs_map
        self.__suppress_handler = suppress_handler
        self.__package_version = package_version
        self.__session = session
        self.report_ident = sqlalchemy.orm.query.Bundle('report_ident',
                                                        Report.id,
                                                        Report.bug_id,
                                                        Report.run_id)

    def __lastBugEventPos(self, report_id):
        """
        This function returns the last BugPathEvent object position which
        belongs to the given report. If no such event is found then None
        returns.
        """
        last = self.__session.query(BugPathEvent) \
            .filter(BugPathEvent.report_id == report_id) \
            .order_by(BugPathEvent.order.desc()) \
            .limit(1).one_or_none()

        if not last:
            return None

        bpe = bugpathevent_db_to_api(last)
        bpe.filePath = self.__session.query(File).get(bpe.fileId).filepath

        return bpe

    def __sortResultsQuery(self, query, sort_types=None):
        """
        Helper method for __queryDiffResults and queryResults to apply sorting.
        """

        # Get a list of sort_types which will be a nested ORDER BY.
        sort_type_map = {SortType.FILENAME: [File.filepath],
                         SortType.CHECKER_NAME: [Report.checker_id],
                         SortType.SEVERITY: [Report.severity]}

        # Mapping the SQLAlchemy functions.
        order_type_map = {Order.ASC: asc, Order.DESC: desc}

        if sort_types is None:
            sort_types = [SortMode(SortType.FILENAME, Order.ASC)]

        for sort in sort_types:
            sorttypes = sort_type_map.get(sort.type)
            for sorttype in sorttypes:
                order_type = order_type_map.get(sort.ord)
                query = query.order_by(order_type(sorttype))

        return query

    @timeit
    def getRunData(self, run_name_filter):

        session = self.__session
        results = []
        try:
            # Count the reports subquery.
            stmt = session.query(Report.run_id,
                                 func.count(literal_column('*')).label(
                                     'report_count')) \
                .group_by(Report.run_id) \
                .subquery()

            q = session.query(Run, stmt.c.report_count)

            if run_name_filter is not None:
                q = q.filter(Run.name.ilike('%' + run_name_filter + '%'))

            q = q.outerjoin(stmt, Run.id == stmt.c.run_id) \
                .order_by(Run.date)

            for instance, reportCount in q:
                if reportCount is None:
                    reportCount = 0

                results.append(RunData(instance.id,
                                       str(instance.date),
                                       instance.name,
                                       instance.duration,
                                       reportCount,
                                       instance.command
                                       ))
            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            LOG.error(str(alchemy_ex))
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              str(alchemy_ex))

    @timeit
    def getReport(self, reportId):
        session = self.__session

        try:
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

            if review_status:
                review_data = ReviewData(
                    status=review_status.status,
                    comment=review_status.message,
                    author=review_status.author,
                    date=str(review_status.date))
            else:
                review_data = ReviewData(
                    status=shared.ttypes.ReviewStatus.UNREVIEWED,
                    comment=None,
                    author=None,
                    date=None)

            return ReportData(
                bugHash=report.bug_id,
                checkedFile=source_file.filepath,
                checkerMsg=report.checker_message,
                reportId=report.id,
                fileId=source_file.id,
                lastBugPosition=self.__lastBugEventPos(report.id),
                checkerId=report.checker_id,
                severity=report.severity,
                review=review_data)
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE,
                msg)

    @timeit
    def getRunResults(self, run_id, limit, offset, sort_types, report_filters):

        max_query_limit = constants.MAX_QUERY_SIZE
        if limit > max_query_limit:
            LOG.debug('Query limit ' + str(limit) +
                      ' was larger than max query limit ' +
                      str(max_query_limit) + ', setting limit to ' +
                      str(max_query_limit))
            limit = max_query_limit

        session = self.__session
        filter_expression = construct_report_filter(report_filters)

        try:

            q = session.query(Report,
                              File,
                              ReviewStatus) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File, Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(filter_expression)

            q = self.__sortResultsQuery(q, sort_types)

            results = []

            for report, source_file, review_status in \
                    q.limit(limit).offset(offset):

                if review_status:
                    review_data = ReviewData(
                        status=review_status.status,
                        comment=review_status.message,
                        author=review_status.author,
                        date=str(review_status.date))
                else:
                    review_data = ReviewData(
                        status=shared.ttypes.ReviewStatus.UNREVIEWED,
                        comment=None,
                        author=None,
                        date=None)

                results.append(
                    ReportData(bugHash=report.bug_id,
                               checkedFile=source_file.filepath,
                               checkerMsg=report.checker_message,
                               reportId=report.id,
                               fileId=source_file.id,
                               lastBugPosition=self.__lastBugEventPos(
                                   report.id),
                               checkerId=report.checker_id,
                               severity=report.severity,
                               review=review_data)
                )

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    @timeit
    def getRunResultCount(self, run_id, report_filters):

        filter_expression = construct_report_filter(report_filters)

        session = self.__session
        try:
            reportCount = session.query(Report) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File, Report.file_id == File.id) \
                .filter(filter_expression) \
                .count()

            if reportCount is None:
                reportCount = 0

            return reportCount

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

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

        session = self.__session
        try:
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

    @timeit
    def changeReviewStatus(self, report_id, status, message):
        """
        Change review status of the bug by report id.
        """
        session = self.__session
        try:
            report = session.query(Report).get(report_id)
            if report:
                review_status = session.query(ReviewStatus).get(report.bug_id)
                if review_status is None:
                    review_status = ReviewStatus()
                    review_status.bug_hash = report.bug_id

                user = self.__auth_session.user \
                    if self.__auth_session else "Anonymous"

                review_status.status = status
                review_status.author = user
                review_status.message = message
                review_status.date = datetime.now()

                session.add(review_status)
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
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE, msg)

    @timeit
    def getComments(self, report_id):
        """
            Return the list of comments for the given bug.
        """
        session = self.__session
        try:
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

    @timeit
    def getCommentCount(self, report_id):
        """
            Return the number of comments for the given bug.
        """
        session = self.__session
        try:
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

    @timeit
    def addComment(self, report_id, comment_data):
        """
            Add new comment for the given bug.
        """
        session = self.__session
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

    @timeit
    def updateComment(self, comment_id, content):
        """
            Update the given comment message with new content. We allow
            comments to be updated by it's original author only, except for
            Anyonymous comments that can be updated by anybody.
        """
        session = self.__session
        user = self.__auth_session.user\
            if self.__auth_session else "Anonymous"
        try:
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

    @timeit
    def removeComment(self, comment_id):
        """
            Remove the comment. We allow comments to be removed by it's
            original author only, except for Anyonymous comments that can be
            updated by anybody.
        """
        user = self.__auth_session.user\
            if self.__auth_session else "Anonymous"
        session = self.__session
        try:
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

    def getCheckerConfigs(self, run_id):
        """
        Parameters:
         - run_id
        """
        session = self.__session
        try:
            configs = session.query(Config) \
                .filter(Config.run_id == run_id) \
                .all()

            configs = [(c.checker_name, c.attribute, c.value)
                       for c in configs]
            res = []
            for cName, attribute, value in configs:
                res.append(shared.ttypes.ConfigValue(cName, attribute, value))

            return res

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    @timeit
    def getSkipPaths(self, run_id):
        session = self.__session
        try:
            suppressed_paths = session.query(SkipPath) \
                .filter(SkipPath.run_id == run_id) \
                .all()

            results = []
            for sp in suppressed_paths:
                encoded_path = sp.path
                encoded_comment = sp.comment
                results.append(SkipPathData(encoded_path, encoded_comment))

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    @timeit
    def getSourceFileData(self, fileId, fileContent, encoding):
        """
        Parameters:
         - fileId
         - fileContent
         - enum Encoding
        """
        session = self.__session
        try:
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

    @timeit
    def getRunResultTypes(self, run_id, report_filters):

        session = self.__session
        try:

            filter_expression = construct_report_filter(report_filters)

            q = session.query(Report) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File, Report.file_id == File.id) \
                .order_by(Report.checker_id) \
                .filter(filter_expression) \
                .all()

            count_results = defaultdict(int)

            result_reports = defaultdict()
            # Count and filter out the results for the same checker_id.
            for r in q:
                count_results[r.checker_id] += 1
                result_reports[r.checker_id] = r

            results = []
            for checker_id, res in result_reports.items():
                results.append(ReportDataTypeCount(checker_id,
                                                   res.severity,
                                                   count_results[checker_id]))

            # Result count ascending.
            results = sorted(results, key=lambda rep: rep.count, reverse=True)

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    # -----------------------------------------------------------------------
    @timeit
    def __get_hashes_for_diff(self, session, base_run_id, new_run_id):

        LOG.debug('query all baseline hashes')
        # Keyed tuple list is returned.
        base_line_hashes = session.query(Report.bug_id) \
            .filter(Report.run_id == base_run_id) \
            .all()

        LOG.debug('query all new check hashes')
        # Keyed tuple list is returned.
        new_check_hashes = session.query(Report.bug_id) \
            .filter(Report.run_id == new_run_id) \
            .all()

        base_line_hashes = set([t[0] for t in base_line_hashes])
        new_check_hashes = set([t[0] for t in new_check_hashes])

        return base_line_hashes, new_check_hashes

    # -----------------------------------------------------------------------
    @timeit
    def __queryDiffResults(self,
                           session,
                           diff_hash_list,
                           run_id,
                           limit,
                           offset,
                           sort_types=None,
                           report_filters=None):

        max_query_limit = constants.MAX_QUERY_SIZE
        if limit > max_query_limit:
            LOG.debug('Query limit ' + str(limit) +
                      ' was larger than max query limit ' +
                      str(max_query_limit) + ', setting limit to ' +
                      str(max_query_limit))
            limit = max_query_limit

        filter_expression = construct_report_filter(report_filters)

        try:
            q = session.query(Report,
                              File,
                              ReviewStatus) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File, Report.file_id == File.id) \
                .outerjoin(ReviewStatus,
                           ReviewStatus.bug_hash == Report.bug_id) \
                .filter(Report.bug_id.in_(diff_hash_list)) \
                .filter(filter_expression)

            q = self.__sortResultsQuery(q, sort_types)

            results = []

            for report, source_file, review_status \
                    in q.limit(limit).offset(offset):

                if review_status:
                    review_data = ReviewData(
                        status=review_status.status,
                        comment=review_status.message,
                        author=review_status.author,
                        date=str(review_status.date))
                else:
                    review_data = ReviewData(
                        status=shared.ttypes.ReviewStatus.UNREVIEWED,
                        comment=None,
                        author=None,
                        date=None)

                results.append(ReportData(
                    bugHash=report.bug_id,
                    checkedFile=source_file.filepath,
                    checkerMsg=report.checker_message,
                    reportId=report.id,
                    fileId=source_file.id,
                    lastBugPosition=self.__lastBugEventPos(report.id),
                    checkerId=report.checker_id,
                    severity=report.severity,
                    review=review_data))

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    # -----------------------------------------------------------------------
    @timeit
    def getNewResults(self,
                      base_run_id,
                      new_run_id,
                      limit,
                      offset,
                      sort_types=None,
                      report_filters=None):

        session = self.__session

        base_line_hashes, new_check_hashes = \
            self.__get_hashes_for_diff(session,
                                       base_run_id,
                                       new_run_id)

        diff_hashes = list(new_check_hashes.difference(base_line_hashes))

        LOG.debug(len(diff_hashes))
        LOG.debug(diff_hashes)

        if len(diff_hashes) == 0:
            return []

        return self.__queryDiffResults(session,
                                       diff_hashes,
                                       new_run_id,
                                       limit,
                                       offset,
                                       sort_types,
                                       report_filters)

    # -----------------------------------------------------------------------
    @timeit
    def getResolvedResults(self,
                           base_run_id,
                           new_run_id,
                           limit,
                           offset,
                           sort_types=None,
                           report_filters=None):

        session = self.__session
        base_line_hashes, new_check_hashes = \
            self.__get_hashes_for_diff(session,
                                       base_run_id,
                                       new_run_id)

        diff_hashes = list(base_line_hashes.difference(new_check_hashes))

        LOG.debug(len(diff_hashes))
        LOG.debug(diff_hashes)

        if len(diff_hashes) == 0:
            return []

        return self.__queryDiffResults(session,
                                       diff_hashes,
                                       base_run_id,
                                       limit,
                                       offset,
                                       sort_types,
                                       report_filters)

    # -----------------------------------------------------------------------
    @timeit
    def getUnresolvedResults(self,
                             base_run_id,
                             new_run_id,
                             limit,
                             offset,
                             sort_types=None,
                             report_filters=None):

        session = self.__session
        base_line_hashes, new_check_hashes = \
            self.__get_hashes_for_diff(session,
                                       base_run_id,
                                       new_run_id)

        diff_hashes = list(base_line_hashes.intersection(new_check_hashes))

        LOG.debug('diff hashes' + str(len(diff_hashes)))
        LOG.debug(diff_hashes)

        if len(diff_hashes) == 0:
            return []

        return self.__queryDiffResults(session,
                                       diff_hashes,
                                       new_run_id,
                                       limit,
                                       offset,
                                       sort_types,
                                       report_filters)

    # -----------------------------------------------------------------------
    @timeit
    def getAPIVersion(self):
        # Returns the thrift api version.
        return constants.API_VERSION

    # -----------------------------------------------------------------------
    @timeit
    def getPackageVersion(self):
        return self.__package_version

    # -----------------------------------------------------------------------
    @timeit
    def removeRunResults(self, run_ids):

        session = self.__session

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
        return True

    # -----------------------------------------------------------------------
    def getSuppressFile(self):
        """
        Return the suppress file path or empty string if not set.
        """
        suppress_file = self.__suppress_handler.suppress_file
        if suppress_file:
            return suppress_file
        return ''

    # -----------------------------------------------------------------------
    def __queryDiffResultsCount(self,
                                session,
                                diff_hash_list,
                                run_id,
                                report_filters=None):
        """
        Count results for a hash list with filters.
        """

        filter_expression = construct_report_filter(report_filters)

        try:
            report_count = session.query(Report) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File, Report.file_id == File.id) \
                .filter(Report.bug_id.in_(diff_hash_list)) \
                .filter(filter_expression) \
                .count()

            if report_count is None:
                report_count = 0

            return report_count

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    # -----------------------------------------------------------------------
    @timeit
    def getDiffResultCount(self,
                           base_run_id,
                           new_run_id,
                           diff_type,
                           report_filters):
        """
        Count the diff results.
        """

        session = self.__session
        base_line_hashes, new_check_hashes = \
            self.__get_hashes_for_diff(session,
                                       base_run_id,
                                       new_run_id)

        if diff_type == DiffType.NEW:
            diff_hashes = list(new_check_hashes.difference(base_line_hashes))
            if not diff_hashes:
                return 0
            run_id = new_run_id

        elif diff_type == DiffType.RESOLVED:
            diff_hashes = list(base_line_hashes.difference(new_check_hashes))
            if not diff_hashes:
                return 0
            run_id = base_run_id

        elif diff_type == DiffType.UNRESOLVED:
            diff_hashes = list(base_line_hashes.intersection(new_check_hashes))
            if not diff_hashes:
                return 0
            run_id = new_run_id

        else:
            msg = 'Unsupported diff type: ' + str(diff_type)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        return self.__queryDiffResultsCount(session,
                                            diff_hashes,
                                            run_id,
                                            report_filters)

    # -----------------------------------------------------------------------
    def __queryDiffResultTypes(self,
                               session,
                               diff_hash_list,
                               run_id,
                               report_filters):
        """
        Query and count results for a hash list with filters.
        """
        try:
            filter_expression = construct_report_filter(report_filters)

            q = session.query(Report) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File, Report.file_id == File.id) \
                .order_by(Report.checker_id) \
                .filter(Report.bug_id.in_(diff_hash_list)) \
                .filter(filter_expression) \
                .all()

            count_results = defaultdict(int)
            result_reports = defaultdict()

            # Count and filter out the results for the same checker_id.
            for r in q:
                count_results[r.checker_id] += 1
                result_reports[r.checker_id] = r

            results = []
            for checker_id, res in result_reports.items():
                results.append(ReportDataTypeCount(res.checker_id,
                                                   res.severity,
                                                   count_results[
                                                       res.checker_id]))

            # Result count ascending.
            results = sorted(results, key=lambda rep: rep.count, reverse=True)
            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    # -----------------------------------------------------------------------
    @timeit
    def getDiffResultTypes(self,
                           base_run_id,
                           new_run_id,
                           diff_type,
                           report_filters):

        session = self.__session
        base_line_hashes, new_check_hashes = \
            self.__get_hashes_for_diff(session,
                                       base_run_id,
                                       new_run_id)

        if diff_type == DiffType.NEW:
            diff_hashes = list(new_check_hashes.difference(base_line_hashes))
            if not diff_hashes:
                return diff_hashes
            run_id = new_run_id

        elif diff_type == DiffType.RESOLVED:
            diff_hashes = list(base_line_hashes.difference(new_check_hashes))
            if not diff_hashes:
                return diff_hashes
            run_id = base_run_id

        elif diff_type == DiffType.UNRESOLVED:
            diff_hashes = list(base_line_hashes.intersection(new_check_hashes))
            if not diff_hashes:
                return diff_hashes
            run_id = new_run_id

        else:
            msg = 'Unsupported diff type: ' + str(diff_type)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

        return self.__queryDiffResultTypes(session,
                                           diff_hashes,
                                           run_id,
                                           report_filters)

    @timeit
    def addCheckerRun(self, command, name, version, force):
        """
        Store checker run related data to the database.
        By default updates the results if name already exists.
        Using the force flag removes existing analysis results for a run.
        """
        try:
            LOG.debug("adding checker run")
            run = self.__session.query(Run).filter(Run.name == name).first()
            if run and force:
                # Clean already collected results.
                if not run.can_delete:
                    # Deletion is already in progress.
                    msg = "Can't delete " + str(run.id)
                    LOG.debug(msg)
                    raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.DATABASE,
                        msg)

                LOG.info('Removing previous analysis results ...')
                self.__session.delete(run)
                self.__session.commit()

                checker_run = Run(name, version, command)
                self.__session.add(checker_run)
                self.__session.commit()
                return checker_run.id

            elif run:
                # There is already a run, update the results.
                run.date = datetime.now()
                # Increment update counter and the command.
                run.inc_count += 1
                run.command = command
                self.__session.commit()
                return run.id
            else:
                # There is no run create new.
                checker_run = Run(name, version, command)
                self.__session.add(checker_run)
                self.__session.commit()
                return checker_run.id
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    @timeit
    def finishCheckerRun(self, run_id):
        """
        """
        try:
            LOG.debug("Finishing checker run")
            run = self.__session.query(Run).get(run_id)
            if not run:
                return False

            run.mark_finished()
            self.__session.commit()
            return True

        except Exception as ex:
            LOG.error(ex)
            return False

    @timeit
    def setRunDuration(self, run_id, duration):
        """
        """
        try:
            LOG.debug("setting run duartion")
            run = self.__session.query(Run).get(run_id)
            if not run:
                return False

            run.duration = duration
            self.__session.commit()
            return True
        except Exception as ex:
            LOG.error(ex)
            return false

    @timeit
    def replaceConfigInfo(self, run_id, config_values):
        """
        Removes all the previously stored config information and stores the
        new values.
        """
        try:
            LOG.debug("Replacing config info")
            count = self.__session.query(Config) \
                .filter(Config.run_id == run_id) \
                .delete()
            LOG.debug('Config: ' + str(count) + ' removed item.')

            configs = [Config(
                run_id, info.checker_name, info.attribute, info.value) for
                info in config_values]
            self.__session.bulk_save_objects(configs)
            self.__session.commit()
            return True

        except Exception as ex:
            LOG.error(ex)
            return False

    @timeit
    def needFileContent(self, filepath, content_hash):
        """
        """
        f = self.__session.query(File) \
            .filter(and_(File.content_hash == content_hash,
                         File.filepath == filepath)) \
            .one_or_none()

        needed = self.__session.query(FileContent).get(content_hash) is None

        if not f or needed:
            try:
                self.__session.commit()
                if needed:
                    # Avoid foreign key errors: add empty content.
                    file_content = FileContent(content_hash, "")
                    self.__session.add(file_content)
                f = File(filepath, content_hash)
                self.__session.add(f)
                self.__session.commit()
            except sqlalchemy.exc.IntegrityError:
                # Other transaction might added the same file in the meantime.
                self.__session.rollback()

        return NeedFileResult(needed, f.id)

    @timeit
    def addFileContent(self, content_hash, content, encoding):
        """
        """
        if encoding == Encoding.BASE64:
            content = base64.b64decode(content)

        compressed_content = zlib.compress(content,
                                           zlib.Z_BEST_COMPRESSION)
        self.__session.commit()
        try:
            file_content = self.__session.query(FileContent).get(content_hash)
            file_content.content = compressed_content
            self.__session.add(file_content)
            self.__session.commit()
        except sqlalchemy.exc.IntegrityError as ex:
            # Other transaction might added the same content in the meantime.
            self.__session.rollback()
            return False
        return True

    def __is_same_event_path(self, report_id, events):
        """
        Checks if the given event path is the same as the one in the
        events argument.
        """
        try:
            q = self.__session.query(BugPathEvent) \
                .filter(BugPathEvent.report_id == report_id) \
                .order_by(BugPathEvent.order)

            len_events = len(events)
            for i, point2 in enumerate(q):
                if i == len_events:
                    return False

                point1 = events[i]

                if point1.startCol != point2.col_begin or \
                        point1.endCol != point2.col_end or \
                        point1.msg != point2.msg or \
                        point1.fileId != point2.file_id:
                    return False

            return True

        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    @timeit
    def storeReportInfo(self,
                        run_id,
                        file_id,
                        bug_hash,
                        msg,
                        bugpath,
                        events,
                        checker_id,
                        checker_cat,
                        bug_type,
                        severity):
        """
        """
        try:
            LOG.debug("getting source file for report")
            source_file = self.__session.query(File).get(file_id)
            _, source_file_name = os.path.split(source_file.filepath)

            LOG.debug("initializing report")
            report = Report(run_id,
                            bug_hash,
                            file_id,
                            msg,
                            checker_id,
                            checker_cat,
                            bug_type,
                            severity)

            self.__session.add(report)
            self.__session.flush()

            LOG.debug("storing bug path")
            self.__storeBugPath(bugpath, report.id)
            LOG.debug("storing events")
            self.__storeBugEvents(events, report.id)

            self.__session.commit()

            return report.id
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    @timeit
    def addReport(self,
                  run_id,
                  file_id,
                  bug_hash,
                  msg,
                  bugpath,
                  events,
                  checker_id,
                  checker_cat,
                  bug_type,
                  severity):
        """
        """
        try:
            checker_id = checker_id or 'NOT FOUND'

            # TODO: performance issues when executing the following query on
            # large databases?
            reports = self.__session.query(self.report_ident) \
                .filter(and_(self.report_ident.c.bug_id == bug_hash,
                             self.report_ident.c.run_id == run_id))
            try:
                # Check for duplicates by bug hash.
                LOG.debug("checking duplicates")
                if reports.count() != 0:
                    for possib_dup in reports:
                        LOG.debug("there is a possible duplicate")
                        # It's a duplicate or a hash clash. Check checker name,
                        # file id, and position.
                        dup_report_obj = self.__session.query(Report).get(
                            possib_dup.report_ident.id)
                        if dup_report_obj and \
                                dup_report_obj.checker_id == checker_id and \
                                dup_report_obj.file_id == file_id and \
                                self.__is_same_event_path(
                                    dup_report_obj.id, events):
                            # TODO: It is not clear why this commit is needed
                            # but if it is not here then the commit in
                            # finishCheckerRun() hangs.
                            self.__session.commit()
                            return dup_report_obj.id

                LOG.debug("no duplicate storing report")
                return self.storeReportInfo(run_id,
                                            file_id,
                                            bug_hash,
                                            msg,
                                            bugpath,
                                            events,
                                            checker_id,
                                            checker_cat,
                                            bug_type,
                                            severity)

            except sqlalchemy.exc.IntegrityError as ex:
                self.__session.rollback()

                reports = self.__session.query(self.report_ident) \
                    .filter(and_(self.report_ident.c.bug_id == bug_hash,
                                 self.report_ident.c.run_id == run_id))
                if reports.count() != 0:
                    return reports.first().report_ident.id
                else:
                    raise
        except Exception as ex:
            self.__session.rollback()
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    def __storeBugEvents(self, bugevents, report_id):
        """
        """
        for i, event in enumerate(bugevents):
            bpe = BugPathEvent(event.startLine,
                               event.startCol,
                               event.endLine,
                               event.endCol,
                               i,
                               event.msg,
                               event.fileId,
                               report_id)

            self.__session.add(bpe)

    def __storeBugPath(self, bugpath, report_id):
        for i, piece in enumerate(bugpath):
            brp = BugReportPoint(piece.startLine,
                                 piece.startCol,
                                 piece.endLine,
                                 piece.endCol,
                                 i,
                                 piece.fileId,
                                 report_id)

            self.__session.add(brp)

    @timeit
    def addSkipPath(self, run_id, paths):
        """
        """
        try:
            count = self.__session.query(SkipPath) \
                .filter(SkipPath.run_id == run_id) \
                .delete()
            LOG.debug('SkipPath: ' + str(count) + ' removed item.')

            skipPathList = []
            for path, comment in paths.items():
                skipPath = SkipPath(run_id, path, comment)
                skipPathList.append(skipPath)
            self.__session.bulk_save_objects(skipPathList)
            self.__session.commit()
            return True
        except Exception as ex:
            LOG.error(str(ex))
            return False
