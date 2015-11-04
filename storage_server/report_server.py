# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import datetime
import socket
import errno
import ntpath

import sqlalchemy
from alembic import command, config
from alembic.migration import MigrationContext

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

from codechecker_gen.DBThriftAPI import CheckerReport
from codechecker_gen.DBThriftAPI.ttypes import *

from db_model.orm_model import *

from codechecker_lib import logger
from codechecker_lib import decorators

LOG = logger.get_new_logger('CC SERVER')

if os.environ.get('CODECHECKER_ALCHEMY_LOG') is not None:
    import logging

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.DEBUG)

class CheckerReportHandler(object):
    '''
    Class to handle requests from the codechecker script to store run
    information to the database.
    '''

    def sequenceDeleter(self, table, first_id):
        """Delete points of sequnce in a general way."""
        next_id = first_id
        while next_id:
            item = self.session.query(table).get(next_id)
            self.session.delete(item)
            next_id = item.next

    def deleteBuildAction(self, build_action):
        """Garbage collector for incremental build."""
        reports = self.session.query(ReportsToBuildActions) \
                              .filter(ReportsToBuildActions.build_action_id ==
                                      build_action.id)

        # Delete all report which is only in the current build action
        for r in reports:
            rid = r.report_id

            reference = self.session.query(ReportsToBuildActions) \
                            .filter(
                                and_(ReportsToBuildActions.report_id == rid,
                                     ReportsToBuildActions.build_action_id != build_action.id)).first()
            if not reference:
                report = self.session.query(Report).get(rid)
                self.sequenceDeleter(BugPathEvent, report.start_bugevent)
                self.sequenceDeleter(BugReportPoint, report.start_bugpoint)
                # The report deletion is not needed because the sqlalchemy does it with relationships

        # TODO: should I delete the files?

        self.session.delete(build_action)  # => delete ReportsToBuildActions
        # ReportsToBuildActions items are deleted by sqlalchemy cascade on delete
        self.session.commit()

    @decorators.catch_sqlalchemy
    def addCheckerRun(self, command, name, version, update):
        '''
        '''
        # TODO: command, version
        # runs = self.session.query(Run).filter(Run.name == name)
        # if runs.count() == 0:
        if not update:
            checkerRun = Run(name, version, command)
            self.session.add(checkerRun)
            self.session.commit()
            return checkerRun.id
        else:
            run = self.session.query(Run).filter(Run.name == name).first()
            if not run:
                # create new run to store results
                checkerRun = Run(name, version, command)
                self.session.add(checkerRun)
                self.session.commit()
                return checkerRun.id

            LOG.info('\033[91mIncremental checking is in progress. The previous run results for '
                     + name + ' will be overwritten! \033[0m')
            run.date = datetime.now()
            run.inc_count += 1
            self.session.commit()
            return run.id

    @decorators.catch_sqlalchemy
    def finishCheckerRun(self, run_id):
        '''
        '''
        run = self.session.query(Run).get(run_id)
        if not run:
            return False

        run.mark_finished()
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    def addConfigInfo(self, run_id, config_values):
        '''
        '''
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
    def addBuildAction(self, run_id, build_cmd, check_cmd):
        '''
        '''
        build_action = \
            self.session.query(BuildAction) \
                        .filter(and_(BuildAction.run_id == run_id,
                                     BuildAction.build_cmd == build_cmd,
                                     BuildAction.check_cmd == check_cmd))
        if build_action.count() != 0:
            # FIXME: should delete this build action only in update mode
            self.deleteBuildAction(build_action.first())

        action = BuildAction(run_id, build_cmd, check_cmd)
        self.session.add(action)
        self.session.commit()
        return action.id

    @decorators.catch_sqlalchemy
    def finishBuildAction(self, action_id, failure):
        '''
        '''
        action = self.session.query(BuildAction).get(action_id)
        if action is None:
            # TODO: if file is not needed update reportstobuildactions
            # accordingly
            return False

        action.mark_finished(failure)
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    def needFileContent(self, run_id, filepath):
        '''
        '''
        f = self.session.query(File) \
                        .filter(and_(File.run_id == run_id,
                                     File.filepath == filepath)) \
                        .first()
        run_inc_count = self.session.query(Run).get(run_id).inc_count
        needed = False
        if not f:
            needed = True
            f = File(run_id, filepath)
            self.session.add(f)
            self.session.commit()  # need to commit
        elif f.inc_count < run_inc_count:
            needed = True
            f.inc_count = run_inc_count
        return NeedFileResult(needed, f.id)

    @decorators.catch_sqlalchemy
    def addFileContent(self, id, content):
        '''
        '''
        f = self.session.query(File).get(id)
        assert f is not None
        f.addContent(content)
        return True

    @decorators.catch_sqlalchemy
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
        '''
        '''

        def is_same_event_path(start_bugevent_id):
            """Checkes if the given event path is the same as the one in the
            events argument
            """

            point2_id = start_bugevent_id
            for point1 in events:
                if point2_id is None:
                    return False

                point2 = self.session.query(BugPathEvent).get(point2_id)
                if point1.startLine != point2.line_begin or \
                   point1.startCol != point2.col_begin or \
                   point1.endLine != point2.line_end or \
                   point1.endCol != point2.col_end or \
                   point1.msg != point2.msg or \
                   point1.fileId != point2.file_id:
                    return False

                point2_id = point2.next

            return point2_id is None

        # TODO: perfomance issues when executing the following query on large
        #       databaseses
        reports = self.session.query(self.report_ident) \
                              .filter(Report.bug_id == bug_hash)

        action = self.session.query(BuildAction).get(build_action_id)
        assert action is not None

        try:
            # Check for duplicates by bug hash
            if reports.count() != 0:
                possib_dups = reports.filter(self.report_ident.c.run_id ==
                                             action.run_id)
                for possib_dup in possib_dups:
                    # It's a duplicate or a hash clash. Check checker name,
                    # file id, and position
                    dup_report_obj = self.session.query(Report).get(
                        possib_dup.report_ident.id)
                    if dup_report_obj.checker_id == checker_id and \
                       dup_report_obj.file_id == file_id and \
                       is_same_event_path(dup_report_obj.start_bugevent):
                        # It's a duplicate
                        rtp = self.session.query(ReportsToBuildActions) \
                                          .get((dup_report_obj.id,
                                                action.id))
                        if not rtp:
                            reportToActions = ReportsToBuildActions(
                                dup_report_obj.id, action.id)
                            self.session.add(reportToActions)
                            self.session.commit()
                        return dup_report_obj.id

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

        except sqlalchemy.exc.IntegrityError:
            self.session.rollback()

            reports = self.session.query(Report) \
                                  .filter(and_(Report.bug_id == bug_hash,
                                               Report.run_id == action.run_id))
            if reports.count() != 0:
                return reports.first().id
            else:
                raise

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
                        suppressed = False):
        '''
        store report information
        '''
        path_ids = self.storeBugPath(bugpath)
        event_ids = self.storeBugEvents(events)
        path_start = path_ids[0].id if len(path_ids) > 0 else None

        source_file = self.session.query(File).get(file_id)
        source_file_path, source_file_name = ntpath.split(source_file.filepath)

        supp = self.session.query(SuppressBug) \
                           .filter(
                               or_(and_(SuppressBug.run_id == action.run_id,
                                        SuppressBug.hash == bug_hash,
                                        SuppressBug.file_name == source_file_name),
                                   and_(SuppressBug.run_id == action.run_id,
                                        SuppressBug.hash == bug_hash,
                                        SuppressBug.file_name == u''))) \
                           .first()

        if supp:
            suppressed = True

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

        self.session.add(report)
        self.session.commit()
        # Flush needs to be done to get the ID of the newly added report.
        reportToActions = ReportsToBuildActions(report.id, action.id)
        self.session.add(reportToActions)
        # Avoid from data loss at key duplicate
        self.session.commit()
        return report.id

    def storeBugEvents(self, bugevents):
        '''
        '''
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
            for i in xrange(len(events)):
                try:
                    events[i].addNext(events[i+1].id)
                    events[i+1].addPrev(events[i].id)

                except IndexError:
                    # we are at the last event
                    if (len(events) != 1):
                        # set prev only if list was longer than one
                        events[i].addPrev(events[i-1].id)
        return events

    def storeBugPath(self, bugpath):
        paths = []
        for i in xrange(len(bugpath)):
            brp = BugReportPoint(bugpath[i].startLine,
                                 bugpath[i].startCol,
                                 bugpath[i].endLine,
                                 bugpath[i].endCol,
                                 bugpath[i].fileId)
            self.session.add(brp)
            paths.append(brp)

        self.session.flush()

        for i in xrange(len(paths)):
            try:
                paths[i].addNext(paths[i+1].id)
            except IndexError:
                # got the the last bug report point
                pass

        return paths

    @decorators.catch_sqlalchemy
    def addSuppressBug(self, run_id, bugs_to_suppress):
        '''
        Supppress multiple bugs for a run this can be used usually
        before the checking to sore the suppress file content
        '''

        try:
            suppressList = []
            for bug_to_suppress in bugs_to_suppress:
                bug_hash = bug_to_suppress.bug_hash
                file_name = bug_to_suppress.file_name
                comment = bug_to_suppress.comment

                suppress_bug = SuppressBug(run_id,
                                           bug_hash,
                                           file_name,
                                           comment)
                suppressList.append(suppress_bug)

            self.session.bulk_save_objects(suppressList)
            self.session.commit()

        except Exception as ex:
            LOG.error(str(ex))
            return False

        return True


    @decorators.catch_sqlalchemy
    def cleanSuppressData(self, run_id):
        '''
        Clean the suppress bug entries for a run
        and remove suppressed flags for the suppressed reports.
        Only the database is modified
        '''

        try:
            count = self.session.query(SuppressBug) \
                                .filter(SuppressBug.run_id == run_id) \
                                .delete()
            LOG.debug('Cleaning previous suppress entries from the database. '
                      + str(count) + ' removed items.')

            reports = self.session.query(Report) \
                         .filter(and_(Report.run_id == run_id,
                                      Report.suppressed == True)) \
                         .all()

            for report in reports:
                report.suppressed = False

            self.session.commit()

        except Exception as ex:
            LOG.error(str(ex))
            return False

        return True


    @decorators.catch_sqlalchemy
    def addSkipPath(self, run_id, paths):
        '''
        '''
        count = self.session.query(SkipPath) \
                            .filter(SkipPath.run_id == run_id) \
                            .delete()
        LOG.debug('SkipPath: ' + str(count) + ' removed item.')

        skipPathList = []
        for path, comment in paths.items():
            skipPath = SkipPath(run_id, path, comment)
            # self.session.add(skipPath)
            # self.session.commit()
            skipPathList.append(skipPath)
        self.session.bulk_save_objects(skipPathList)
        self.session.commit()
        return True

    @decorators.catch_sqlalchemy
    def stopServer(self):
        '''
        '''
        self.session.commit()
        sys.exit(0)

    def __init__(self, session, lockDB):
        self.session = session
        self.report_ident = sqlalchemy.orm.query.Bundle('report_ident',
                                                        Report.id,
                                                        Report.bug_id,
                                                        Report.run_id,
                                                        Report.start_bugevent,
                                                        Report.start_bugpoint)


def create_db_if_not_exists(uri, db_name):
    ''' True -> created, False -> already exists and do nothing. '''
    LOG.debug('Creating new database if not exists')

    db_uri = os.path.join(uri, 'postgres')
    LOG.debug(db_uri)

    engine = sqlalchemy.create_engine(db_uri, client_encoding='utf8')

    text = "SELECT 1 FROM pg_database WHERE datname='%s'" % db_name
    if not bool(engine.execute(text).scalar()):
        conn = engine.connect()
        conn.execute('commit')
        conn.execute('create database "%s"' % db_name)
        conn.close()

        LOG.debug('Database created: ' + db_name)
        return True

    LOG.debug('Database already exists: ' + db_name)
    return False

def migrate_database(session, migration_scripts):
    LOG.debug('Updating schema to HEAD...')

    connection = session.connection()

    cfg = config.Config()
    cfg.set_main_option("script_location", migration_scripts)
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")

def run_server(dbUsername, port, db_name, dbhost, dbport, db_version_info, migration_scripts, callback_event=None):
    LOG.debug('Starting codechecker server ...')

    uri = 'postgres://' + dbUsername + '@' + dbhost + ':' + str(dbport)

    try:

        ret = create_db_if_not_exists(uri, db_name)
        LOG.debug('Database exists: ' + str(ret))
    except sqlalchemy.exc.SQLAlchemyError as alch_err:
        LOG.error(str(alch_err))
        sys.exit(1)

    try:
        db_uri = os.path.join(uri, db_name)
        engine = sqlalchemy.create_engine(db_uri, strategy='threadlocal')

        LOG.debug('DB Engine: '+str(engine))

        LOG.debug('Creating new database session')
        session = CreateSession(engine)

        LOG.debug('Creating new database schema')
        start = datetime.now()
        migrate_database(session, migration_scripts)
        end = datetime.now()
        diff = end - start
        LOG.debug('Creating new database schema done in ' + str(diff.seconds))

        version = session.query(DBVersion).first()
        if version is None:
            # Version is not populated yet
            expected = db_version_info.get_expected_version()
            session.add(DBVersion(expected[0], expected[1]))
            session.commit()
        elif db_version_info.is_compatible(version.major,
                                           version.minor):
            LOG.error('Version mismatch. Expected database version: ' +
                      str(db_version_info))
            version_from_db = 'v'+str(version.major)+'.'+str(version.minor)
            LOG.error('Version from the database is: ' + version_from_db)
            LOG.error('Please update your database.')
            sys.exit(1)

    except sqlalchemy.exc.SQLAlchemyError as alch_err:
        LOG.error(str(alch_err))
        sys.exit(1)
    finally:
        session.commit()

    session.autoflush = False  # autoflush is enabled by default

    LOG.debug('Starting thrift server')
    try:
        # Start thrift server
        handler = CheckerReportHandler(session, True)

        processor = CheckerReport.Processor(handler)
        transport = TSocket.TServerSocket(port=port)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()

        server = TServer.TThreadPoolServer(processor,
                                           transport,
                                           tfactory,
                                           pfactory,
                                           daemon=True)

        LOG.info('Waiting for check results on ['+str(port)+']')
        if callback_event:
            callback_event.set()
        LOG.debug('Starting to serve')
        server.serve()
    except socket.error as sockerr:
        LOG.error(str(sockerr))
        if sockerr.errno == errno.EADDRINUSE:
            LOG.error('Checker port '+str(port)+' is already used')
        sys.exit(1)
    except Exception as err:
        LOG.error(str(err))
        session.commit()
        sys.exit(1)
