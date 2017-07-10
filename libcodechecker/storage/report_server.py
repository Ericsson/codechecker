# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals

import datetime
import errno
import os
import socket
import sys

import sqlalchemy

from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from thrift.transport import TSocket
from thrift.transport import TTransport

from DBThriftAPI import CheckerReport
from DBThriftAPI.ttypes import *

from libcodechecker import database_handler
from libcodechecker import decorators
from libcodechecker.logger import LoggerFactory
from libcodechecker.orm_model import *
from libcodechecker.profiler import timeit

LOG = LoggerFactory.get_new_logger('CC SERVER')

if os.environ.get('CODECHECKER_ALCHEMY_LOG') is not None:
    import logging

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.DEBUG)


class CheckerReportHandler(object):
    """
    Class to handle requests from the CodeChecker script to store run
    information to the database.
    """

    @decorators.catch_sqlalchemy
    @timeit
    def addCheckerRun(self, command, name, version, force):
        """
        Store checker run related data to the database.
        By default updates the results if name already exists.
        Using the force flag removes existing analysis results for a run.
        """
        run = self.session.query(Run).filter(Run.name == name).first()
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
            self.session.delete(run)
            self.session.commit()

            checker_run = Run(name, version, command)
            self.session.add(checker_run)
            self.session.commit()
            return checker_run.id

        elif run:
            # There is already a run, update the results.
            run.date = datetime.now()
            # Increment update counter and the command.
            run.inc_count += 1
            run.command = command
            self.session.commit()
            return run.id
        else:
            # There is no run create new.
            checker_run = Run(name, version, command)
            self.session.add(checker_run)
            self.session.commit()
            return checker_run.id

    @decorators.catch_sqlalchemy
    @timeit
    def finishCheckerRun(self, run_id):
        """
        """
        run = self.session.query(Run).get(run_id)
        if not run:
            return False

        run.mark_finished()
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    @timeit
    def setRunDuration(self, run_id, duration):
        """
        """
        run = self.session.query(Run).get(run_id)
        if not run:
            return False

        run.duration = duration
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    @timeit
    def replaceConfigInfo(self, run_id, config_values):
        """
        Removes all the previously stored config information and stores the
        new values.
        """
        count = self.session.query(Config) \
            .filter(Config.run_id == run_id) \
            .delete()
        LOG.debug('Config: ' + str(count) + ' removed item.')

        configs = [Config(
            run_id, info.checker_name, info.attribute, info.value) for
            info in config_values]
        self.session.bulk_save_objects(configs)
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    @timeit
    def needFileContent(self, run_id, filepath):
        """
        """
        try:
            f = self.session.query(File) \
                .filter(and_(File.run_id == run_id,
                             File.filepath == filepath)) \
                .one_or_none()
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

        run_inc_count = self.session.query(Run).get(run_id).inc_count
        needed = False
        if not f:
            needed = True
            f = File(run_id, filepath)
            self.session.add(f)
            self.session.commit()
        elif f.inc_count < run_inc_count:
            needed = True
            f.inc_count = run_inc_count
        return NeedFileResult(needed, f.id)

    @decorators.catch_sqlalchemy
    @timeit
    def addFileContent(self, id, content):
        """
        """
        f = self.session.query(File).get(id)
        assert f is not None
        f.addContent(content)
        return True

    def __is_same_event_path(self, start_bugevent_id, events):
        """
        Checks if the given event path is the same as the one in the
        events argument.
        """
        try:
            # There should be at least one bug event.
            point2 = self.session.query(BugPathEvent).get(start_bugevent_id)

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

                point2 = self.session.query(BugPathEvent).get(point2.next)

        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

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
                        severity,
                        suppressed=False,
                        detection_status='new'):
        """
        """
        try:
            path_ids = self.storeBugPath(bugpath)
            event_ids = self.storeBugEvents(events)
            path_start = path_ids[0].id if len(path_ids) > 0 else None

            source_file = self.session.query(File).get(file_id)
            _, source_file_name = os.path.split(source_file.filepath)

            # Old suppress format did not contain file name.
            suppressed = self.session.query(SuppressBug).filter(
                and_(SuppressBug.run_id == run_id,
                     SuppressBug.hash == bug_hash,
                     or_(SuppressBug.file_name == source_file_name,
                         SuppressBug.file_name == u''))).count() > 0

            report = Report(run_id,
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
                            suppressed,
                            detection_status)

            self.session.add(report)
            self.session.commit()
            return report.id
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    @decorators.catch_sqlalchemy
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
                  severity,
                  suppress):
        """
        """
        try:
            checker_id = checker_id or 'NOT FOUND'

            # Theoretically this query should return at most one result because
            # path hash makes a bug unique in a run.
            # TODO: Add path hash to the query condition.
            reports = self.session.query(self.report_ident) \
                .filter(and_(self.report_ident.c.bug_id == bug_hash,
                             self.report_ident.c.run_id == run_id))
            try:
                # Check for duplicates by bug hash.
                for possib_dup in reports:
                    dup_report_obj = self.session.query(Report).get(
                        possib_dup.report_ident.id)
                    # TODO: file_id and path equality check won't be necessary
                    # when path hash is added.
                    if dup_report_obj and \
                            dup_report_obj.checker_id == checker_id and \
                            dup_report_obj.file_id == file_id and \
                            self.__is_same_event_path(
                                dup_report_obj.start_bugevent, events):

                        new_status = None

                        if dup_report_obj.detection_status == 'new' or \
                                dup_report_obj.detection_status == 'reopened':
                            new_status = 'unresolved'
                        elif dup_report_obj.detection_status == 'resolved':
                            new_status = 'reopened'

                        if new_status:
                            dup_report_obj.detection_status = new_status

                        self.session.commit()
                        return dup_report_obj.id

                return self.storeReportInfo(run_id,
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
                self.session.rollback()

                reports = self.session.query(self.report_ident) \
                    .filter(and_(self.report_ident.c.bug_id == bug_hash,
                                 self.report_ident.c.run_id == run_id))
                if reports.count() != 0:
                    return reports.first().report_ident.id
                else:
                    raise
        except Exception as ex:
            raise shared.ttypes.RequestFailed(
                shared.ttypes.ErrorCode.GENERAL,
                str(ex))

    def markReportsFixed(self, run_id, skip_report_ids):
        self.session.query(Report) \
            .filter(Report.id.notin_(skip_report_ids)) \
            .update({Report.detection_status: 'resolved'},
                    synchronize_session='fetch')
        self.session.commit()
        return True

    def storeBugEvents(self, bugevents):
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
            self.session.add(bpe)
            events.append(bpe)

        self.session.flush()

        if len(events) > 1:
            for i in range(len(events) - 1):
                events[i].addNext(events[i + 1].id)
                events[i + 1].addPrev(events[i].id)
            events[-1].addPrev(events[-2].id)
        return events

    def storeBugPath(self, bugpath):
        paths = []
        for piece in bugpath:
            brp = BugReportPoint(piece.startLine,
                                 piece.startCol,
                                 piece.endLine,
                                 piece.endCol,
                                 piece.fileId)
            self.session.add(brp)
            paths.append(brp)

        self.session.flush()

        for i in range(len(paths) - 1):
            paths[i].addNext(paths[i + 1].id)

        return paths

    @decorators.catch_sqlalchemy
    @timeit
    def addSuppressBug(self, run_id, bugs_to_suppress):
        """
        Supppress multiple bugs for a run. This can be used before storing
        the suppress file content.
        """

        try:
            for bug_to_suppress in bugs_to_suppress:
                res = self.session.query(SuppressBug) \
                    .filter(SuppressBug.hash == bug_to_suppress.bug_hash,
                            SuppressBug.run_id == run_id,
                            SuppressBug.file_name == bug_to_suppress.file_name)

                if res.one_or_none():
                    res.update({'comment': bug_to_suppress.comment})
                else:
                    self.session.add(SuppressBug(run_id,
                                                 bug_to_suppress.bug_hash,
                                                 bug_to_suppress.file_name,
                                                 bug_to_suppress.comment))

            self.session.commit()

        except Exception as ex:
            LOG.error(str(ex))
            return False

        return True

    @decorators.catch_sqlalchemy
    @timeit
    def cleanSuppressData(self, run_id):
        """
        Clean the suppress bug entries for a run
        and remove suppressed flags for the suppressed reports.
        Only the database is modified.
        """

        try:
            count = self.session.query(SuppressBug) \
                .filter(SuppressBug.run_id == run_id) \
                .delete()
            LOG.debug('Cleaning previous suppress entries from the database.'
                      '{0} removed items.'.format(str(count)))

            reports = self.session.query(Report) \
                .filter(and_(Report.run_id == run_id,
                             Report.suppressed)) \
                .all()

            for report in reports:
                report.suppressed = False

            self.session.commit()

        except Exception as ex:
            LOG.error(str(ex))
            return False

        return True

    @decorators.catch_sqlalchemy
    @timeit
    def addSkipPath(self, run_id, paths):
        """
        """
        count = self.session.query(SkipPath) \
            .filter(SkipPath.run_id == run_id) \
            .delete()
        LOG.debug('SkipPath: ' + str(count) + ' removed item.')

        skipPathList = []
        for path, comment in paths.items():
            skipPath = SkipPath(run_id, path, comment)
            skipPathList.append(skipPath)
        self.session.bulk_save_objects(skipPathList)
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    @timeit
    def stopServer(self):
        """
        """
        self.session.commit()
        sys.exit(0)

    def __init__(self, session):
        self.session = session
        self.report_ident = sqlalchemy.orm.query.Bundle('report_ident',
                                                        Report.id,
                                                        Report.bug_id,
                                                        Report.run_id,
                                                        Report.start_bugevent,
                                                        Report.start_bugpoint)


def run_server(port, db_uri, callback_event=None):
    LOG.debug('Starting CodeChecker server ...')

    try:
        engine = database_handler.SQLServer.create_engine(db_uri)

        LOG.debug('Creating new database session.')
        session = CreateSession(engine)

    except sqlalchemy.exc.SQLAlchemyError as alch_err:
        LOG.error(str(alch_err))
        sys.exit(1)

    session.autoflush = False  # Autoflush is enabled by default.

    LOG.debug('Starting thrift server.')
    try:
        # Start thrift server.
        handler = CheckerReportHandler(session)

        processor = CheckerReport.Processor(handler)
        transport = TSocket.TServerSocket(port=port)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()

        server = TServer.TThreadPoolServer(processor,
                                           transport,
                                           tfactory,
                                           pfactory,
                                           daemon=True)

        LOG.info('Waiting for check results on [' + str(port) + ']')
        if callback_event:
            callback_event.set()
        LOG.debug('Starting to serve.')
        server.serve()
        session.commit()
    except socket.error as sockerr:
        LOG.error(str(sockerr))
        if sockerr.errno == errno.EADDRINUSE:
            LOG.error('Checker port ' + str(port) + ' is already used!')
        sys.exit(1)
    except Exception as err:
        LOG.error(str(err))
        session.commit()
        sys.exit(1)
