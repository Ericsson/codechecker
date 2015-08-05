# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
Handle thrift requests
'''
import zlib
import os
import datetime
from collections import defaultdict

import sqlalchemy
from sqlalchemy import asc, desc, insert, exc
from sqlalchemy.sql import or_, and_, func

from db_model.orm_model import *

import shared
from codeCheckerDBAccess import constants
from codeCheckerDBAccess.ttypes import *

from codechecker_lib import logger

LOG = logger.get_new_logger('ACCESS HANDLER')


# -----------------------------------------------------------------------
def timefunc(function):
    '''
    timer function
    '''

    func_name = function.__name__

    def debug_wrapper(*args, **kwargs):
        '''
        wrapper for debug log
        '''
        before = datetime.now()
        res = function(*args, **kwargs)
        after = datetime.now()
        timediff = after - before
        diff = timediff.microseconds/1000
        LOG.debug('['+str(diff)+'ms] ' + func_name)
        return res

    def release_wrapper(*args, **kwargs):
        '''
        no logging
        '''
        res = function(*args, **kwargs)
        return res

    if logger.get_log_level() == logger.DEBUG:
        return debug_wrapper
    else:
        return release_wrapper


# -----------------------------------------------------------------------
def conv(text):
    '''
    Convert * to % got from clients for the database queries
    '''
    if text is None:
        return '%'
    return text.replace('*', '%')


# -----------------------------------------------------------------------
def construct_report_filter(report_filters):
    '''
    construct the report filter for reports and suppressed reports
    '''

    OR = []
    if report_filters is None:
        AND = []
        AND.append(Report.checker_message.like('%'))
        AND.append(Report.checker_id.like('%'))
        AND.append(File.filepath.like('%'))

        OR.append(and_(*AND))
        filter_expression = or_(*OR)
        return filter_expression

    for report_filter in report_filters:
        AND = []
        if report_filter.checkerMsg:
            AND.append(Report.checker_message.like(
                       conv(report_filter.checkerMsg)))
        if report_filter.checkerId:
            AND.append(Report.checker_id.like(
                       conv(report_filter.checkerId)))
        if report_filter.filepath:
            AND.append(File.filepath.like(
                       conv(report_filter.filepath)))
        if report_filter.severity is not None:
            # severity value can be 0
            AND.append(Report.severity == report_filter.severity)
        if report_filter.suppressed:
            AND.append(Report.suppressed == 'True')
        else:
            AND.append(Report.suppressed == 'False')

        OR.append(and_(*AND))

    filter_expression = or_(*OR)

    return filter_expression


# -----------------------------------------------------------------------
class ThriftRequestHandler():
    '''
    Connect to database and handle thrift client requests
    '''

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

        version = self.__session.query(DBVersion).first()
        if version:
            version_from_db = 'v'+str(version.major)+'.'+str(version.minor)
            if db_version_info.is_compatible(version.major,
                                             version.minor):
                LOG.debug('Version mismatch. Expected database version: '
                          + str(db_version_info))
                LOG.debug('Version from the database is: ' + version_from_db)
                LOG.debug('Please update your database.')
                sys.exit(1)
        else:
            LOG.debug('No version information found in the database.')
            LOG.debug('Please check your config')
            sys.exit(1)

    # -----------------------------------------------------------------------
    def __queryResults(self, run_id, limit, offset, sort_types, report_filters):

        max_query_limit = constants.MAX_QUERY_SIZE
        if limit > max_query_limit:
            LOG.debug('Query limit ' + str(limit)
                      + ' was larger than max query limit '
                      + str(max_query_limit) + ', setting limit to '
                      + str(max_query_limit))
            limit = max_query_limit

        session = self.__session

        # get a list of sort_types which will be a nested orderby
        sort_type_map = {}
        sort_type_map[SortType.FILENAME] =  File.filepath
        sort_type_map[SortType.CHECKER_NAME] =  Report.checker_id
        sort_type_map[SortType.SEVERITY] = Report.severity

        #mapping the sqlalchemy functions
        order_type_map = {}
        order_type_map[Order.ASC] = asc
        order_type_map[Order.DESC] = desc

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

            if sort_types is None:
                sorttype = File.filepath
                order_type = asc
                q = q.order_by(order_type(sorttype))
            else:
                for sort in sort_types:
                    sorttype = sort_type_map.get(sort.type)
                    order_type = order_type_map.get(sort.ord)
                    q = q.order_by(order_type(sorttype))

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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

    # -----------------------------------------------------------------------
    @timefunc
    def getRunData(self):

        session = self.__session
        results = []
        try:
            # count the reports subquery
            stmt = session.query(Report.run_id, \
                                 func.count('*').label('report_count')) \
                                 .filter(Report.suppressed == False) \
                                 .group_by(Report.run_id) \
                                 .subquery()

            q = session.query(Run, stmt.c.report_count) \
                              .outerjoin(stmt, Run.id==stmt.c.run_id) \
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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)


    # -----------------------------------------------------------------------
    @timefunc
    def getRunResults(self, run_id, limit, offset, sort_types, report_filters):

        return self.__queryResults(run_id,
                                   limit,
                                   offset,
                                   sort_types,
                                   report_filters)

    # -----------------------------------------------------------------------
    @timefunc
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
                .filter(filter_expression)\
                .count()

            if reportCount is None:
                reportCount = 0

            return reportCount

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

    # -----------------------------------------------------------------------
    @timefunc
    def __construct_bug_event_list(self, session, start_bug_event):

        file_path_cache = {}
        bug_events = []
        event = session.query(BugPathEvent).get(start_bug_event)


        file_path = file_path_cache.get(event.file_id)
        if not file_path:
            f = session.query(File).get(event.file_id)
            file_path = f.filepath
            file_path_cache[event.file_id] = file_path


        bug_events.append((event,file_path))

        while event.next is not None:

            file_path = file_path_cache.get(event.file_id)
            if not file_path:
                f = session.query(File).get(event.file_id)
                file_path = f.filepath
                file_path_cache[event.file_id] = file_path

            event = session.query(BugPathEvent).get(event.next)
            bug_events.append((event,file_path))

        return bug_events


    # -----------------------------------------------------------------------
    @timefunc
    def __construct_bug_point_list(self, session, start_bug_point):
        #start_bug_point can be None

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

                file_path = file_path_cache.get(bug_point.file_id)
                if not file_path:
                    f = session.query(File).get(bug_point.file_id)
                    file_path = f.filepath
                    file_path_cache[bug_point.file_id] = file_path

                bug_point = session.query(BugReportPoint).get(bug_point.next)
                bug_points.append((bug_point, file_path))

        return bug_points


    # -----------------------------------------------------------------------
    @timefunc
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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)


    # -----------------------------------------------------------------------
    @timefunc
    def suppressBug(self, runIds, reportId, comment):
        session = self.__session
        try:
            report = session.query(Report).get(reportId)
            report_hash = report.bug_id
            hash_type = report.bug_id_type

            suppressed = session.query(SuppressBug) \
                                .filter(SuppressBug.hash == report_hash) \
                                .all()

            file_id = report.file_id
            source_file = session.query(File).get(report.file_id)

            if suppressed is None:
                #the bug is not suppressed for any run_id
                #info('storing to database')

                for rId in runIds:
                    suppress_bug = SuppressBug(rId,
                                              report_hash,
                                              hash_type,
                                              comment)
                    session.add(suppress_bug)

                rep = session.query(Report) \
                             .filter(and_(Report.bug_id == report_hash,
                                          Report.run_id.in_(runIds)))
                for r in rep:
                    r.suppressed = True

                ret = self.__suppress_handler \
                           .store_suppress_bug_id(source_file.filepath,
                                                 report_hash,
                                                 hash_type,
                                                 comment)

                if not ret:
                    session.rollback()
                    raise shared.ttypes.RequestFailed(
                                        shared.ttypes.ErrorCode.IOERROR,
                                        'Failed to store suppress bug id')
                else:
                    session.commit()
                    return True

            # bug is suppressed in these runids
            # should be suppressed only once for each runid
            suppressedRunId = set([ r.run_id for r in suppressed])

            # in the newly got runids and are not in the already
            # suppressed set
            toSuppressRunIds = set(runIds).difference(suppressedRunId)
            LOG.debug(toSuppressRunIds)

            for rId in toSuppressRunIds:
                LOG.debug('writing hash and runid to the suppressTable : ' + str(rId) \
                                                                  +' : '+report_hash)
                suppress_bug = SuppressBug(rId, report_hash, hash_type, comment)
                session.add(suppress_bug)

            rep = session.query(Report).filter(and_(Report.bug_id == report_hash, Report.run_id.in_(toSuppressRunIds)))
            for r in rep:
                r.suppressed = True

            LOG.debug(hash_type)
            ret = self.__suppress_handler.store_suppress_bug_id(source_file.filepath, report_hash, hash_type, comment)
            if not ret:
                session.rollback()
                raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR, 'Failed to store suppress bug id')
            else:
                session.commit()
                return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR, msg)


    # -----------------------------------------------------------------------
    @timefunc
    def unSuppressBug(self, runIds, reportId):
        """
        Parameters:
         - runIds
         - reportId
        """
        session = self.__session
        try:
            report = session.query(Report).get(reportId)
            report_hash = report.bug_id
            hash_type = report.bug_id_type

            suppressed = session.query(SuppressBug) \
                            .filter(SuppressBug.hash == report_hash) \
                            .all()


            file_id = report.file_id
            source_file = session.query(File).get(report.file_id)

            if suppressed is None:
                session.commit()
                return True

            # in the got runids and are in the suppressed set
            toUnSuppress = filter(lambda bug: bug.run_id in runIds, set(suppressed))
            toUnSuppressRunIds = {bug.run_id for bug in toUnSuppress}
            LOG.debug(toUnSuppress)

            for bug in toUnSuppress:
                LOG.debug('removing hash and runid from the suppressTable : ' + str(bug.run_id) \
                                                                  + ' : ' + report_hash)
                session.delete(bug)

            rep = session.query(Report).filter(and_(Report.bug_id == report_hash, Report.run_id.in_(toUnSuppressRunIds)))
            for r in rep:
                r.suppressed = False

            LOG.debug(hash_type)
            ret = self.__suppress_handler \
                        .remove_suppress_bug_id(source_file.filepath,
                                               report_hash,
                                               hash_type)
            if not ret:
                session.rollback()
                raise shared.ttypes.RequestFailed(
                        shared.ttypes.ErrorCode.IOERROR,
                        'Failed to remove suppress bug id')
            else:
                session.commit()
                return True

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

        except Exception as ex:
            msg = str(ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR, msg)


    # -----------------------------------------------------------------------
    def getCheckerDoc(self, checkerId):
        """
        Parameters:
         - checkerId
        """

        text = "No documentation for checker: "+checkerId
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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.IOERROR, msg)


    # -----------------------------------------------------------------------
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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

    # -----------------------------------------------------------------------
    @timefunc
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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

    # -----------------------------------------------------------------------
    @timefunc
    def getBuildActions(self, reportId):

        session = self.__session
        try:
            build_actions = session.query(BuildAction) \
                                   .outerjoin(ReportsToBuildActions) \
                                   .filter(ReportsToBuildActions.report_id
                                           == reportId) \
                                   .all()

            return [ba.build_cmd for ba in build_actions]

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)


    # -----------------------------------------------------------------------
    @timefunc
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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)


    # -----------------------------------------------------------------------
    @timefunc
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

            if fileContent:
                source = zlib.decompress(sourcefile.content)

                return SourceFileData(fileId = sourcefile.id, \
                                        filePath=sourcefile.filepath, \
                                        fileContent = source)
            else:
                return SourceFileData(fileId = sourcefile.id, \
                                        filePath=sourcefile.filepath)


        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)


    # -----------------------------------------------------------------------
    @timefunc
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
                .order_by(Report.checker_id) \
                .filter(filter_expression) \
                .all()

            count_results = defaultdict(int)

            result_reports = defaultdict()
            # count and filter out the results for the same checker_id
            for r in q:
                count_results[r.checker_id] += 1
                result_reports[r.checker_id] = r

            results = []
            for checker_id, res in result_reports.items():

                results.append(ReportDataTypeCount(res.checker_id, res.severity, count_results[res.checker_id]))

            # result count ascending
            results = sorted(results, key=lambda rep: rep.count, reverse = True)

            return results

        except sqlalchemy.exc.SQLAlchemyError as alchemy_ex:
            msg = str(alchemy_ex)
            LOG.error(msg)
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

    # -----------------------------------------------------------------------
    @timefunc
    def __get_hashes_for_diff(self, session, base_run_id, new_run_id):

        LOG.debug('query all baseline hashes')
        # keyed tuple list is returned
        base_line_hashes = session.query(Report.bug_id) \
                                         .filter(Report.run_id == base_run_id) \
                                         .all()
        #LOG.debug(len(base_line_hashes))

        LOG.debug('query all new check hashes')
        # keyed tuple list is returned
        new_check_hashes = session.query(Report.bug_id) \
                                         .filter(Report.run_id == new_run_id) \
                                         .all()
        #LOG.debug(len(new_check_hashes))

        base_line_hashes = set([t[0] for t in base_line_hashes])
        new_check_hashes = set([t[0] for t in new_check_hashes])

        return base_line_hashes, new_check_hashes

    # -----------------------------------------------------------------------
    @timefunc
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
            LOG.debug('Query limit ' + str(limit)
                      + ' was larger than max query limit '
                      + str(max_query_limit) + ', setting limit to '
                      + str(max_query_limit))
            limit = max_query_limit

        sort_type_map = {}
        sort_type_map[SortType.FILENAME] = File.filepath
        sort_type_map[SortType.CHECKER_NAME] = Report.checker_id
        sort_type_map[SortType.SEVERITY] = Report.severity

        #mapping the sqlalchemy functions
        order_type_map = {}
        order_type_map[Order.ASC] = asc
        order_type_map[Order.DESC] = desc

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


            if sort_types is None:
                sorttype = File.filepath
                order_type = asc
                q = q.order_by(order_type(sorttype))
            else:
                for sort in sort_types:
                    sorttype = sort_type_map.get(sort.type)
                    order_type = order_type_map.get(sort.ord)
                    q = q.order_by(order_type(sorttype))

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
            raise shared.ttypes.RequestFailed(shared.ttypes.ErrorCode.DATABASE, msg)

    # -----------------------------------------------------------------------
    @timefunc
    def getNewResults(self,
                      base_run_id,
                      new_run_id,
                      limit,
                      offset,
                      sort_types=None,
                      report_filters=None):

        diff_res = []
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
    @timefunc
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
    @timefunc
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
    @timefunc
    def getAPIVersion(self):
        # returns the thrift api version
        return constants.API_VERSION

    # -----------------------------------------------------------------------
    @timefunc
    def removeRunResults(self, run_ids):

        session = self.__session

        for run_id in run_ids:
            LOG.debug('run ids to delete')
            LOG.debug(run_id)

            run_to_delete = session.query(Run).get(run_id)
            session.delete(run_to_delete)

            session.commit()

        return True
