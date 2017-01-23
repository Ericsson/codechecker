# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle thrift requests.
"""

from collections import defaultdict
import codecs
import ntpath
import os
import zlib

from sqlalchemy.sql.expression import false
from sqlalchemy.sql.expression import true
import sqlalchemy

import shared

from codeCheckerDBAccess import constants
from codeCheckerDBAccess.ttypes import *

from codechecker_lib.logger import LoggerFactory
from codechecker_lib.profiler import timeit

from db_model.orm_model import *

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
                 db_version_info):

        self.__checker_md_docs = checker_md_docs
        self.__checker_doc_map = checker_md_docs_map
        self.__suppress_handler = suppress_handler
        self.__session = session

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
                    "Report " + reportId + " not found!")

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
        sort_type_map = {}
        sort_type_map[SortType.FILENAME] = [File.filepath,
                                            BugPathEvent.line_begin]
        sort_type_map[SortType.CHECKER_NAME] = [Report.checker_id]
        sort_type_map[SortType.SEVERITY] = [Report.severity]

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
            report, file_obj = data
            source_file_path, f_name = ntpath.split(file_obj.filepath)
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

        for report, file_obj in reports:
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
        source_file_path, source_file_name = ntpath.split(source_file.filepath)

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
            text += "[ClangSA](" + sa_checkers_link + ")"
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
    def getSourceFileData(self, fileId, fileContent):
        """
        Parameters:
         - fileId
         - fileContent
        """
        session = self.__session
        try:
            sourcefile = session.query(File) \
                .filter(File.id == fileId).first()

            if sourcefile is None:
                return SourceFileData()

            if fileContent and sourcefile.content:
                source = zlib.decompress(sourcefile.content)

                source = codecs.decode(source, 'utf-8', 'replace')

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
