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
        if report_filter.suppressed:
            AND.append(Report.suppressed == true())
        else:
            AND.append(Report.suppressed == false())

        OR.append(and_(*AND))

    filter_expression = or_(*OR)

    return filter_expression


class ThriftRequestHandler():
    """
    Connect to database and handle thrift client requests.
    """

    def __init__(self,
                 session,
                 checker_md_docs,
                 checker_md_docs_map,
                 suppress_handler,
                 db_version_info,
                 package_version):

        self.__checker_md_docs = checker_md_docs
        self.__checker_doc_map = checker_md_docs_map
        self.__suppress_handler = suppress_handler
        self.__package_version = package_version
        self.__session = session
        self.report_ident = sqlalchemy.orm.query.Bundle('report_ident',
                                                        Report.id,
                                                        Report.bug_id,
                                                        Report.run_id,
                                                        Report.start_bugevent,
                                                        Report.start_bugpoint)

    def __queryReport(self, reportId):
        session = self.__session

        try:
            q = session.query(Report,
                              File,
                              BugPathEvent,
                              SuppressBug) \
                .filter(Report.id == reportId) \
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           SuppressBug.hash == Report.bug_id)

            results = q.limit(1).all()
            if len(results) < 1:
                raise shared.ttypes.RequestFailed(
                    shared.ttypes.ErrorCode.DATABASE,
                    "Report " + str(reportId) + " not found!")

            report, source_file, lbpe, suppress_bug = results[0]

            last_event_pos = \
                shared.ttypes.BugPathEvent(
                    startLine=lbpe.line_begin,
                    startCol=lbpe.col_begin,
                    endLine=lbpe.line_end,
                    endCol=lbpe.col_end,
                    msg=lbpe.msg,
                    fileId=lbpe.file_id,
                    filePath=source_file.filepath)

            if suppress_bug:
                suppress_comment = suppress_bug.comment
            else:
                suppress_comment = None

            return ReportData(
                bugHash=report.bug_id,
                checkedFile=source_file.filepath,
                checkerMsg=report.checker_message,
                suppressed=report.suppressed,
                reportId=report.id,
                fileId=source_file.id,
                lastBugPosition=last_event_pos,
                checkerId=report.checker_id,
                severity=report.severity,
                suppressComment=suppress_comment)
        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.DATABASE,
                msg)

    def __sortResultsQuery(self, query, sort_types=None):
        """
        Helper method for __queryDiffResults and __queryResults to apply
        sorting.
        """

        # Get a list of sort_types which will be a nested ORDER BY.
        sort_type_map = {SortType.FILENAME: [File.filepath,
                                             BugPathEvent.line_begin],
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

    def __queryResults(self, run_id, limit, offset, sort_types,
                       report_filters):

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
                              BugPathEvent,
                              SuppressBug) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File,
                           and_(Report.file_id == File.id,
                                File.run_id == run_id)) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           and_(SuppressBug.hash == Report.bug_id,
                                SuppressBug.run_id == run_id)) \
                .filter(filter_expression)

            q = self.__sortResultsQuery(q, sort_types)

            results = []
            for report, source_file, lbpe, suppress_bug in \
                    q.limit(limit).offset(offset):

                last_event_pos = \
                    shared.ttypes.BugPathEvent(startLine=lbpe.line_begin,
                                               startCol=lbpe.col_begin,
                                               endLine=lbpe.line_end,
                                               endCol=lbpe.col_end,
                                               msg=lbpe.msg,
                                               fileId=lbpe.file_id,
                                               filePath=source_file.filepath)

                if suppress_bug:
                    suppress_comment = suppress_bug.comment
                else:
                    suppress_comment = None

                results.append(
                    ReportData(bugHash=report.bug_id,
                               checkedFile=source_file.filepath,
                               checkerMsg=report.checker_message,
                               suppressed=report.suppressed,
                               reportId=report.id,
                               fileId=source_file.id,
                               lastBugPosition=last_event_pos,
                               checkerId=report.checker_id,
                               severity=report.severity,
                               suppressComment=suppress_comment)
                )

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    @timeit
    def getRunData(self):

        session = self.__session
        results = []
        try:
            # Count the reports subquery.
            stmt = session.query(Report.run_id,
                                 func.count(literal_column('*')).label(
                                     'report_count')) \
                .filter(Report.suppressed == false()) \
                .group_by(Report.run_id) \
                .subquery()

            q = session.query(Run, stmt.c.report_count) \
                .outerjoin(stmt, Run.id == stmt.c.run_id) \
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
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    @timeit
    def getReport(self, reportId):
        return self.__queryReport(reportId)

    @timeit
    def getRunResults(self, run_id, limit, offset, sort_types, report_filters):

        return self.__queryResults(run_id,
                                   limit,
                                   offset,
                                   sort_types,
                                   report_filters)

    @timeit
    def getRunResultCount(self, run_id, report_filters):

        filter_expression = construct_report_filter(report_filters)

        session = self.__session
        try:
            reportCount = session.query(Report) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File,
                           and_(Report.file_id == File.id,
                                File.run_id == run_id)) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           and_(SuppressBug.hash == Report.bug_id,
                                SuppressBug.run_id == run_id)) \
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
    def __construct_bug_event_list(self, session, start_bug_event):

        file_path_cache = {}
        bug_events = []
        event = session.query(BugPathEvent).get(start_bug_event)

        file_path = file_path_cache.get(event.file_id)
        if not file_path:
            f = session.query(File).get(event.file_id)
            file_path = f.filepath
            file_path_cache[event.file_id] = file_path

        bug_events.append((event, file_path))

        while event.next is not None:

            event = session.query(BugPathEvent).get(event.next)

            file_path = file_path_cache.get(event.file_id)
            if not file_path:
                f = session.query(File).get(event.file_id)
                file_path = f.filepath
                file_path_cache[event.file_id] = file_path

            bug_events.append((event, file_path))

        return bug_events

    @timeit
    def __construct_bug_point_list(self, session, start_bug_point):
        # Start_bug_point can be None.

        file_path_cache = {}
        bug_points = []

        if start_bug_point:

            bug_point = session.query(BugReportPoint).get(start_bug_point)
            file_path = file_path_cache.get(bug_point.file_id)
            if not file_path:
                f = session.query(File).get(bug_point.file_id)
                file_path = f.filepath
                file_path_cache[bug_point.file_id] = file_path

            bug_points.append((bug_point, file_path))
            while bug_point.next is not None:

                bug_point = session.query(BugReportPoint).get(bug_point.next)

                file_path = file_path_cache.get(bug_point.file_id)
                if not file_path:
                    f = session.query(File).get(bug_point.file_id)
                    file_path = f.filepath
                    file_path_cache[bug_point.file_id] = file_path

                bug_points.append((bug_point, file_path))

        return bug_points

    @timeit
    def getReportDetails(self, reportId):
        """
        Parameters:
         - reportId
        """

        session = self.__session
        try:
            report = session.query(Report).get(reportId)

            events = self.__construct_bug_event_list(session,
                                                     report.start_bugevent)
            bug_events_list = []
            for (event, file_path) in events:
                bug_events_list.append(
                    shared.ttypes.BugPathEvent(
                        startLine=event.line_begin,
                        startCol=event.col_begin,
                        endLine=event.line_end,
                        endCol=event.col_end,
                        msg=event.msg,
                        fileId=event.file_id,
                        filePath=file_path))

            points = self.__construct_bug_point_list(session,
                                                     report.start_bugpoint)

            bug_point_list = []
            for (bug_point, file_path) in points:
                bug_point_list.append(
                    shared.ttypes.BugPathPos(
                        startLine=bug_point.line_begin,
                        startCol=bug_point.col_begin,
                        endLine=bug_point.line_end,
                        endCol=bug_point.col_end,
                        fileId=bug_point.file_id,
                        filePath=file_path))

            return ReportDetails(bug_events_list, bug_point_list)

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    def __set_report_suppress_flag(self,
                                   session,
                                   run_ids,
                                   bug_id_hash,
                                   source_file_name,
                                   suppress_flag):
        """
        Update the suppress flag for multiple report entries based on the
        filter.
        """

        if not run_ids:
            # There are no run ids where the report should be suppressed.
            return

        def check_filename(data):
            _, file_obj = data
            _, f_name = os.path.split(file_obj.filepath)
            if f_name == source_file_name:
                return True
            else:
                return False

        reports = session.query(Report, File) \
            .filter(and_(Report.bug_id == bug_id_hash,
                         Report.run_id.in_(run_ids))) \
            .outerjoin(File, File.id == Report.file_id) \
            .all()

        reports = filter(check_filename, reports)

        for report, _ in reports:
            report.suppressed = suppress_flag

    def __update_suppress_storage_data(self,
                                       run_ids,
                                       report,
                                       suppress,
                                       comment=u''):
        """
        Update suppress information in the database and in the suppress file
        can be used to suppress or unsuppress a report for multiple runs.
        """
        session = self.__session

        report_id = report.id
        bug_id_hash = report.bug_id

        source_file = session.query(File).get(report.file_id)
        _, source_file_name = os.path.split(source_file.filepath)

        LOG.debug('Updating suppress data for: {0} bug id {1}'
                  'file name {2} supressing {3}'.format(report_id,
                                                        bug_id_hash,
                                                        source_file_name,
                                                        suppress))

        # Check if it is already suppressed for any run ids.
        suppressed = session.query(SuppressBug) \
            .filter(or_(
                and_(SuppressBug.hash == bug_id_hash,
                     SuppressBug.file_name == source_file_name,
                     SuppressBug.run_id.in_(run_ids)),
                and_(SuppressBug.hash == bug_id_hash,
                     SuppressBug.file_name == '',
                     SuppressBug.run_id.in_(run_ids))
                )) \
            .all()

        if not suppressed and suppress:
            # The bug is not suppressed for any run_id, suppressing it.
            LOG.debug('Bug is not suppressed in any runs')
            for rId in run_ids:
                suppress_bug = SuppressBug(rId,
                                           bug_id_hash,
                                           source_file_name,
                                           comment)
                session.add(suppress_bug)

            # Update report entries.
            self.__set_report_suppress_flag(session,
                                            run_ids,
                                            bug_id_hash,
                                            source_file_name,
                                            suppress_flag=suppress)

        elif suppressed and suppress:
            # Already suppressed for some run ids check if other suppression
            # is needed for other run id.
            suppressed_runids = set([r.run_id for r in suppressed])
            LOG.debug('Bug is suppressed in these runs:' +
                      ' '.join([str(r) for r in suppressed_runids]))
            suppress_in_these_runs = set(run_ids).difference(suppressed_runids)
            for run_id in suppress_in_these_runs:
                suppress_bug = SuppressBug(run_id,
                                           bug_id_hash,
                                           source_file_name,
                                           comment)
                session.add(suppress_bug)
            self.__set_report_suppress_flag(session,
                                            suppress_in_these_runs,
                                            bug_id_hash,
                                            source_file_name,
                                            suppress_flag=suppress)

        elif suppressed and not suppress:
            # Already suppressed for some run ids
            # remove those entries.
            already_suppressed_runids = \
                filter(lambda bug: bug.run_id in run_ids, set(suppressed))

            unsuppress_in_these_runs = \
                {bug.run_id for bug in already_suppressed_runids}

            LOG.debug('Already suppressed, unsuppressing now')
            suppressed = session.query(SuppressBug) \
                .filter(and_(SuppressBug.hash == bug_id_hash,
                             SuppressBug.file_name == source_file_name,
                             SuppressBug.run_id.in_(unsuppress_in_these_runs)))
            # Delete suppress bug entries.
            for sp in suppressed:
                session.delete(sp)

            # Update report entries.
            self.__set_report_suppress_flag(session,
                                            unsuppress_in_these_runs,
                                            bug_id_hash,
                                            source_file_name,
                                            suppress_flag=suppress)

        # elif suppressed is None and not suppress:
        #    # check only in the file if there is anything that should be
        #    # removed the database has no entries in the suppressBug table

        if suppress:
            # Store to suppress file.
            ret = self.__suppress_handler \
                .store_suppress_bug_id(bug_id_hash,
                                       source_file_name,
                                       comment)
        else:
            # Remove from suppress file.
            ret = self.__suppress_handler \
                .remove_suppress_bug_id(bug_id_hash,
                                        source_file_name)

        if not ret:
            session.rollback()
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR,
                                              'Failed to store suppress bugId')
        else:
            session.commit()
            return True

    @timeit
    def suppressBug(self, run_ids, report_id, comment):
        """
        Add suppress bug entry to the SuppressBug table.
        Set the suppressed flag for the selected report.
        """
        session = self.__session
        try:
            report = session.query(Report).get(report_id)
            if report:
                return self.__update_suppress_storage_data(run_ids,
                                                           report,
                                                           True,
                                                           comment)
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

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.IOERROR, msg)

    @timeit
    def unSuppressBug(self, run_ids, report_id):
        """
        Remove the suppress flag from the reports in multiple runs if given.
        Cleanup the SuppressBug table to remove suppress entries.
        """
        session = self.__session
        try:
            report = session.query(Report).get(report_id)
            if report:
                return self.__update_suppress_storage_data(run_ids,
                                                           report,
                                                           False)
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

    def getSuppressedBugs(self, run_id):
        """
        Return the list of suppressed bugs in the given run.
        """
        session = self.__session
        try:
            result = []

            suppressed = session.query(SuppressBug) \
                .filter(SuppressBug.run_id == run_id).all()

            for suppression in suppressed:
                result.append(shared.ttypes.SuppressBugData(
                    suppression.hash,
                    suppression.file_name,
                    suppression.comment))

            return result

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
    def getBuildActions(self, reportId):

        session = self.__session
        try:
            build_actions = session.query(BuildAction) \
                .outerjoin(ReportsToBuildActions) \
                .filter(ReportsToBuildActions.report_id == reportId) \
                .all()

            return [BuildActionData(id=ba.id,
                                    runId=ba.run_id,
                                    buildCmd=ba.build_cmd_hash,
                                    analyzerType=ba.analyzer_type,
                                    file=ba.analyzed_source_file,
                                    checkCmd=ba.check_cmd,
                                    failure=ba.failure_txt,
                                    date=str(ba.date),
                                    duration=ba.duration) for ba in
                    build_actions]

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE,
                                              msg)

    @timeit
    def getFileId(self, run_id, path):

        session = self.__session

        try:
            sourcefile = session.query(File) \
                .filter(File.run_id == run_id,
                        File.filepath == path) \
                .first()

            if sourcefile is None:
                return -1

            return sourcefile.id

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
            sourcefile = session.query(File) \
                .filter(File.id == fileId).first()

            if sourcefile is None:
                return SourceFileData()

            if fileContent and sourcefile.content:
                source = zlib.decompress(sourcefile.content)

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
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           and_(SuppressBug.hash == Report.bug_id,
                                SuppressBug.run_id == run_id)) \
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
                              BugPathEvent,
                              SuppressBug) \
                .filter(Report.run_id == run_id) \
                .outerjoin(File,
                           and_(Report.file_id == File.id,
                                File.run_id == run_id)) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           and_(SuppressBug.hash == Report.bug_id,
                                SuppressBug.run_id == run_id)) \
                .filter(Report.bug_id.in_(diff_hash_list)) \
                .filter(filter_expression)

            q = self.__sortResultsQuery(q, sort_types)

            results = []
            for report, source_file, lbpe, suppress_bug \
                    in q.limit(limit).offset(offset):

                lastEventPos = \
                    shared.ttypes.BugPathEvent(startLine=lbpe.line_begin,
                                               startCol=lbpe.col_begin,
                                               endLine=lbpe.line_end,
                                               endCol=lbpe.col_end,
                                               msg=lbpe.msg,
                                               fileId=lbpe.file_id)

                if suppress_bug:
                    suppress_comment = suppress_bug.comment
                else:
                    suppress_comment = None
                results.append(ReportData(bugHash=report.bug_id,
                                          checkedFile=source_file.filepath,
                                          checkerMsg=report.checker_message,
                                          suppressed=report.suppressed,
                                          reportId=report.id,
                                          fileId=source_file.id,
                                          lastBugPosition=lastEventPos,
                                          checkerId=report.checker_id,
                                          severity=report.severity,
                                          suppressComment=suppress_comment))

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
            LOG.debug('run ids to delete')
            LOG.debug(run_id)

            run_to_delete = session.query(Run).get(run_id)
            if not run_to_delete.can_delete:
                LOG.debug("Can't delete " + str(run_id))
                continue

            run_to_delete.can_delete = False
            session.commit()
            runs_to_delete.append(run_to_delete)

        for run_to_delete in runs_to_delete:
            session.delete(run_to_delete)
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
                .outerjoin(File,
                           and_(Report.file_id == File.id,
                                File.run_id == run_id)) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           and_(SuppressBug.hash == Report.bug_id,
                                SuppressBug.run_id == run_id)) \
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
                .outerjoin(File,
                           Report.file_id == File.id) \
                .outerjoin(BugPathEvent,
                           Report.end_bugevent == BugPathEvent.id) \
                .outerjoin(SuppressBug,
                           and_(SuppressBug.hash == Report.bug_id,
                                SuppressBug.run_id == run_id)) \
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

    def __sequence_deleter(self, table, first_id):
        """Delete points of sequence in a general way."""
        next_id = first_id
        while next_id:
            item = self.__session.query(table).get(next_id)
            if item:
                next_id = item.next
                self.__session.delete(item)
            else:
                break

    def __del_source_file_for_report(self, run_id, report_id, report_file_id):
        """
        Delete the stored file if there are no report references to it
        in the database.
        """
        report_reference_to_file = self.__session.query(Report) \
            .filter(
            and_(Report.run_id == run_id,
                 Report.file_id == report_file_id,
                 Report.id != report_id))
        rep_ref_count = report_reference_to_file.count()
        if rep_ref_count == 0:
            LOG.debug("No other references to the source file \n id: " +
                      str(report_file_id) + " can be deleted.")
            # There are no other references to the file, it can be deleted.
            self.__session.query(File).filter(File.id == report_file_id) \
                .delete()
        return rep_ref_count

    def __del_buildaction_results(self, build_action_id, run_id):
        """
        Delete the build action and related analysis results from the database.

        Report entry will be deleted by ReportsToBuildActions cascade delete.
        """
        LOG.debug("Cleaning old buildactions")

        try:
            rep_to_ba = self.__session.query(ReportsToBuildActions) \
                .filter(ReportsToBuildActions.build_action_id ==
                        build_action_id)

            reports_to_delete = [r.report_id for r in rep_to_ba]

            LOG.debug("Trying to delete reports belonging to the buildaction:")
            LOG.debug(reports_to_delete)

            for report_id in reports_to_delete:
                # Check if there is another reference to this report from
                # other buildactions.
                other_reference = self.__session.query(ReportsToBuildActions) \
                    .filter(
                    and_(ReportsToBuildActions.report_id == report_id,
                         ReportsToBuildActions.build_action_id !=
                         build_action_id))

                LOG.debug("Checking report id:" + str(report_id))

                LOG.debug("Report id " + str(report_id) +
                          " reference count: " +
                          str(other_reference.count()))

                if other_reference.count() == 0:
                    # There is no other reference, data related to the report
                    # can be deleted.
                    report = self.__session.query(Report).get(report_id)
                    if report:
                        LOG.debug("Removing bug path events.")
                        self.__sequence_deleter(BugPathEvent,
                                                report.start_bugevent)
                        LOG.debug("Removing bug report points.")
                        self.__sequence_deleter(BugReportPoint,
                                                report.start_bugpoint)

                        if self.__del_source_file_for_report(run_id, report.id,
                                                             report.file_id):
                            LOG.debug("Stored source file needs to be kept, "
                                      "there is reference to it from another "
                                      "report.")
                            # Report needs to be deleted if there is
                            # no reference the file cascade delete will
                            # remove it else manual cleanup is needed.
                            self.__session.delete(report)
                    else:
                        LOG.debug("Report migth be deleted already")

            self.__session.query(BuildAction).filter(
                BuildAction.id == build_action_id) \
                .delete()

            self.__session.query(ReportsToBuildActions).\
                filter(ReportsToBuildActions.build_action_id ==
                       build_action_id).\
                delete()
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

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
    def addBuildAction(self,
                       run_id,
                       build_cmd_hash,
                       check_cmd,
                       analyzer_type,
                       analyzed_source_file):
        """
        """
        try:
            LOG.debug("Storign buildaction")
            LOG.debug(run_id)
            LOG.debug(build_cmd_hash)
            LOG.debug(check_cmd)
            LOG.debug(analyzer_type)
            LOG.debug(analyzed_source_file)

            build_actions = \
                self.__session.query(BuildAction) \
                    .filter(
                    and_(BuildAction.run_id == run_id,
                         BuildAction.build_cmd_hash == build_cmd_hash,
                         or_(
                             and_(
                                 BuildAction.analyzer_type == analyzer_type,
                                 BuildAction.analyzed_source_file ==
                                 analyzed_source_file),
                             and_(BuildAction.analyzer_type == "",
                                  BuildAction.analyzed_source_file == "")
                         ))) \
                    .all()

            if build_actions:
                # Delete the already stored buildaction and analysis results.
                for build_action in build_actions:
                    self.__del_buildaction_results(build_action.id, run_id)

                self.__session.commit()

            action = BuildAction(run_id,
                                 build_cmd_hash,
                                 check_cmd,
                                 analyzer_type,
                                 analyzed_source_file)
            self.__session.add(action)
            self.__session.commit()

            return action.id

        except Exception as ex:
            LOG.error(ex)
            raise

    @timeit
    def finishBuildAction(self, action_id, failure):
        """
        """
        try:
            action = self.__session.query(BuildAction).get(action_id)
            if action is None:
                # TODO: if file is not needed update reportsToBuildActions.
                return False

            failure = \
                failure.decode('unicode_escape').encode('ascii', 'ignore')

            action.mark_finished(failure)
            self.__session.commit()
            return True

        except Exception as ex:
            LOG.error(ex)
            return False

    @timeit
    def needFileContent(self, run_id, filepath):
        """
        """
        try:
            f = self.__session.query(File) \
                .filter(and_(File.run_id == run_id,
                             File.filepath == filepath)) \
                .one_or_none()
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

        run_inc_count = self.__session.query(Run).get(run_id).inc_count
        needed = False
        if not f:
            needed = True
            f = File(run_id, filepath)
            self.__session.add(f)
            self.__session.commit()
        elif f.inc_count < run_inc_count:
            needed = True
            f.inc_count = run_inc_count
            self.__session.commit()
        return NeedFileResult(needed, f.id)

    @timeit
    def addFileContent(self, fid, content, encoding):
        """
        """
        if encoding == Encoding.BASE64:
            content = base64.b64decode(content)

        try:
            f = self.__session.query(File).get(fid)
            compresssed_content = zlib.compress(content,
                                                zlib.Z_BEST_COMPRESSION)
            f.addContent(compresssed_content)
            self.__session.commit()
            return True

        except Exception as ex:
            LOG.debug(ex)
            return False

    def __is_same_event_path(self, start_bugevent_id, events):
        """
        Checks if the given event path is the same as the one in the
        events argument.
        """
        try:
            # There should be at least one bug event.
            point2 = self.__session.query(BugPathEvent).get(start_bugevent_id)

            for point1 in events:
                if point1.startLine != point2.line_begin or \
                        point1.startCol != point2.col_begin or \
                        point1.endLine != point2.line_end or \
                        point1.endCol != point2.col_end or \
                        point1.msg != point2.msg or \
                        point1.fileId != point2.file_id:
                    return False

                if point2.next is None:
                    return point1 == events[-1]

                point2 = self.__session.query(BugPathEvent).get(point2.next)

        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    @timeit
    def storeReportInfo(self,
                        action,
                        file_id,
                        bug_hash,
                        msg,
                        bugpath,
                        events,
                        checker_id,
                        checker_cat,
                        bug_type,
                        severity,
                        suppressed=False):
        """
        """
        try:
            LOG.debug("storing bug path")
            path_ids = self.__storeBugPath(bugpath)
            LOG.debug("storing events")
            event_ids = self.__storeBugEvents(events)
            path_start = path_ids[0].id if len(path_ids) > 0 else None

            LOG.debug("getting source file for report")
            source_file = self.__session.query(File).get(file_id)
            _, source_file_name = os.path.split(source_file.filepath)

            LOG.debug("Checking if suppressed")
            # Old suppress format did not contain file name.
            suppressed = self.__session.query(SuppressBug).filter(
                and_(SuppressBug.run_id == action.run_id,
                     SuppressBug.hash == bug_hash,
                     or_(SuppressBug.file_name == source_file_name,
                         SuppressBug.file_name == u''))).count() > 0

            LOG.debug("initializing report")
            report = Report(action.run_id,
                            bug_hash,
                            file_id,
                            msg,
                            path_start,
                            event_ids[0].id,
                            event_ids[-1].id,
                            checker_id,
                            checker_cat,
                            bug_type,
                            severity,
                            suppressed)

            self.__session.add(report)
            self.__session.commit()
            LOG.debug("extending reports to ba table")
            # Commit required to get the ID of the newly added report.
            reportToActions = ReportsToBuildActions(report.id, action.id)
            self.__session.add(reportToActions)
            # Avoid data loss for duplicate keys.
            self.__session.commit()
            LOG.debug("Storing report done")
            return report.id
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    @timeit
    def addReport(self,
                  build_action_id,
                  file_id,
                  bug_hash,
                  msg,
                  bugpath,
                  events,
                  checker_id,
                  checker_cat,
                  bug_type,
                  severity,
                  suppress):
        """
        """
        try:
            LOG.debug("store report")
            action = self.__session.query(BuildAction).get(build_action_id)
            assert action is not None

            checker_id = checker_id or 'NOT FOUND'

            # TODO: performance issues when executing the following query on
            # large databases?
            reports = self.__session.query(self.report_ident) \
                .filter(and_(self.report_ident.c.bug_id == bug_hash,
                             self.report_ident.c.run_id == action.run_id))
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
                                    dup_report_obj.start_bugevent, events):
                            # It's a duplicate.
                            LOG.debug("it is a duplicate")
                            rtp = self.__session.query(ReportsToBuildActions) \
                                .get((dup_report_obj.id,
                                      action.id))
                            if not rtp:
                                LOG.debug("no rep to ba entry found")
                                reportToActions = ReportsToBuildActions(
                                    dup_report_obj.id, action.id)
                                self.__session.add(reportToActions)
                                self.__session.commit()
                            LOG.debug("rep to ba entry found")
                            LOG.debug("returning duplicate id")
                            LOG.debug(dup_report_obj.id)

                            return dup_report_obj.id

                LOG.debug("no duplicate storing report")
                return self.storeReportInfo(action,
                                            file_id,
                                            bug_hash,
                                            msg,
                                            bugpath,
                                            events,
                                            checker_id,
                                            checker_cat,
                                            bug_type,
                                            severity,
                                            suppress)

            except sqlalchemy.exc.IntegrityError as ex:
                self.__session.rollback()

                reports = self.__session.query(self.report_ident) \
                    .filter(and_(self.report_ident.c.bug_id == bug_hash,
                                 self.report_ident.c.run_id == action.run_id))
                if reports.count() != 0:
                    return reports.first().report_ident.id
                else:
                    raise
        except Exception as ex:
            self.__session.rollback()
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    def __storeBugEvents(self, bugevents):
        """
        """
        events = []
        for event in bugevents:
            bpe = BugPathEvent(event.startLine,
                               event.startCol,
                               event.endLine,
                               event.endCol,
                               event.msg,
                               event.fileId)
            self.__session.add(bpe)
            events.append(bpe)

        self.__session.flush()

        if len(events) > 1:
            for i in range(len(events) - 1):
                events[i].addNext(events[i + 1].id)
                events[i + 1].addPrev(events[i].id)
            events[-1].addPrev(events[-2].id)
        return events

    def __storeBugPath(self, bugpath):
        paths = []
        for piece in bugpath:
            brp = BugReportPoint(piece.startLine,
                                 piece.startCol,
                                 piece.endLine,
                                 piece.endCol,
                                 piece.fileId)
            self.__session.add(brp)
            paths.append(brp)

        self.__session.flush()

        for i in range(len(paths) - 1):
            paths[i].addNext(paths[i + 1].id)

        return paths

    @timeit
    def addSuppressBug(self, run_id, bugs_to_suppress):
        """
        Supppress multiple bugs for a run. This can be used before storing
        the suppress file content.
        """

        try:
            for bug_to_suppress in bugs_to_suppress:
                res = self.__session.query(SuppressBug) \
                    .filter(SuppressBug.hash == bug_to_suppress.bug_hash,
                            SuppressBug.run_id == run_id,
                            SuppressBug.file_name == bug_to_suppress.file_name)

                if res.one_or_none():
                    res.update({'comment': bug_to_suppress.comment})
                else:
                    self.__session.add(SuppressBug(run_id,
                                                   bug_to_suppress.bug_hash,
                                                   bug_to_suppress.file_name,
                                                   bug_to_suppress.comment))

            self.__session.commit()
            return True

        except Exception as ex:
            LOG.error(str(ex))
            return False

    @timeit
    def cleanSuppressData(self, run_id):
        """
        Clean the suppress bug entries for a run
        and remove suppressed flags for the suppressed reports.
        Only the database is modified.
        """

        try:
            count = self.__session.query(SuppressBug) \
                .filter(SuppressBug.run_id == run_id) \
                .delete()
            LOG.debug('Cleaning previous suppress entries from the database.'
                      '{0} removed items.'.format(str(count)))

            reports = self.__session.query(Report) \
                .filter(and_(Report.run_id == run_id,
                             Report.suppressed)) \
                .all()

            for report in reports:
                report.suppressed = False

            self.__session.commit()
            return True

        except Exception as ex:
            LOG.error(str(ex))
            return False

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
