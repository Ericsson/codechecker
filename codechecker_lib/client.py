import re
import sys
import zlib
import time
import atexit
import contextlib
import multiprocessing

import shared
from storage_server import report_server

from DBThriftAPI import CheckerReport
from DBThriftAPI.ttypes import *

from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from codechecker_lib import logger
from codechecker_lib import plist_parser
from codechecker_lib import database_handler
from codechecker_lib import util
from codechecker_lib import suppress_file_handler

LOG = logger.get_new_logger('CLIENT')


# -----------------------------------------------------------------------------
def send_plist_content(connection, plist_file, build_action_id, run_id,
                       severity_map, should_skip):
    try:
        files, bugs = plist_parser.parse_plist(plist_file)
    except Exception:
        LOG.info('The generated plist is not valid, so parsing failed.')
        return

    file_ids = {}
    # Send content of file to the server if needed
    for file_name in files:
        file_descriptor = connection.need_file_content(file_name)
        file_ids[file_name] = file_descriptor.fileId
        if file_descriptor.needed:
            with open(file_name, 'r') as source_file:
                file_content = source_file.read()
            compressed_file = zlib.compress(file_content, zlib.Z_BEST_COMPRESSION)
            # TODO: we may not use the file content in the end
            # depending on skippaths
            connection.add_file_content(file_descriptor.fileId, compressed_file)

    report_ids = []
    for bug in bugs:
        events = bug.events()
        if events and should_skip(events[-1].start_pos.file_path):
            # Issue #20: this bug is in a file which should be skipped
            LOG.debug(bug.hash_value + ' is skipped (in ' +
                      events[-1].start_pos.file_path + ")")
            continue

        # create remaining data for bugs and send them to the server
        bug_paths = []
        for path in bug.paths():
            bug_paths.append(shared.ttypes.BugPathPos(path.start_pos.line,
                                                      path.start_pos.col, path.end_pos.line, path.end_pos.col,
                                                      file_ids[path.start_pos.file_path]))

        bug_events = []
        for event in bug.events():
            bug_events.append(shared.ttypes.BugPathEvent(event.start_pos.line,
                event.start_pos.col, event.end_pos.line, event.end_pos.col,
                event.msg, file_ids[event.start_pos.file_path]))

        bug_hash = bug.hash_value
        bug_hash_type = bug.hash_type
        LOG.debug('Bug hash: ' + bug_hash)
        LOG.debug('Bug hash type: ' + str(bug_hash_type))

        severity_name = severity_map.get(bug.checker_name, 'UNSPECIFIED')
        severity = shared.ttypes.Severity._NAMES_TO_VALUES[severity_name]

        report_id = connection.add_report(build_action_id,
                                          file_ids[bug.file_path],
                                          bug_hash,
                                          bug_hash_type,
                                          bug.msg,
                                          bug_paths,
                                          bug_events,
                                          bug.checker_name,
                                          bug.category,
                                          bug.type,
                                          severity)

        report_ids.append(report_id)


# -----------------------------------------------------------------------------
def send_suppress(connection, file_name):

    hashes, paths = suppress_file_handler.get_hash_and_path(file_name)

    if len(hashes) > 0:
        connection.add_suppress_bug(hashes)
    if len(paths) > 0:
        connection.add_skip_paths(paths)


# -----------------------------------------------------------------------------
def send_config(connection, file_name):
    ''' Send the config file content to the server. '''
    configs = []
    with open(file_name, 'r') as config_file:
        checker_name = ''
        for line in config_file:
            result = re.match('^\[(.*)\]$', line)
            if result:
                checker_name = result.group(1)
            else:
                result = re.match('^(.*)=(.*)$', line)
                if result:
                    key = result.group(1)
                    key_value = result.group(2)
                    configs.append(shared.ttypes.ConfigValue(checker_name, key,
                                                             key_value))

    connection.add_config_info(configs)

# -----------------------------------------------------------------------------
# def send_skiplist(connection, lst):
#     ''' Send skip path to the server. '''
#     connection.add_skip_path(lst)


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def get_connection():
    ''' Automatic Connection handler via ContextManager idiom.
        You can use this in with statement.'''
    connection = Connection()

    try:
        yield connection
    finally:
        connection.close_connection()


# -----------------------------------------------------------------------------
class Connection(object):
    ''' Represent a connection to the server.
        In contstructor establish the connection and
        you have to call close_connection function to close it.
        Information what this use come from ConnectionManager class.
        So, you should set it up before create a connection.'''

    def __init__(self):
        ''' Establish the connection beetwen client and server. '''
        tries_count = 0
        while True:
            try:
                self._transport = TSocket.TSocket(ConnectionManager.host,
                                                   ConnectionManager.port)
                self._transport = TTransport.TBufferedTransport(self._transport)
                self._protocol = TBinaryProtocol.TBinaryProtocol(self._transport)
                self._client = CheckerReport.Client(self._protocol)
                self._transport.open()
                break

            except Thrift.TException as thrift_exc:
                if tries_count > 3:
                    LOG.error('The client cannot establish the connection '
                              'with the server!')
                    LOG.error('%s' % (thrift_exc.message))
                    sys.exit(2)
                else:
                    tries_count += 1
                    time.sleep(1)

    def close_connection(self):
        ''' Close connection. '''
        self._transport.close()

    def add_checker_run(self, command, name, version, update):
        ''' i64  addCheckerRun(1: string command, 2: string name,
                               3: string version) '''
        run_id = self._client.addCheckerRun(command, name, version, update)
        ConnectionManager.run_id = run_id
        return run_id

    def finish_checker_run(self, run_id=None):
        ''' bool finishCheckerRun(1: i64 run_id) '''
        if run_id is None:
            self._client.finishCheckerRun(ConnectionManager.run_id)
        else:
            self._client.finishCheckerRun(run_id)

    def add_suppress_bug(self, bug_hash):
        '''bool addSuppressBug(1: i64 run_id, 2: map<string, string> hashes)'''
        converted = {}
        for path, comment in bug_hash.items():
            converted[path] = comment.encode('UTF-8')
        return self._client.addSuppressBug(ConnectionManager.run_id, converted)

    def add_skip_paths(self, paths):
        ''' bool addSkipPath(1: i64 run_id, 2: map<string, string> paths) '''
        # convert before sending through thrift
        converted = {}
        for path, comment in paths.items():
            converted[path] = comment.encode('UTF-8')
        return self._client.addSkipPath(ConnectionManager.run_id, converted)

    def add_config_info(self, config_list):
        ''' bool addConfigInfo(1: i64 run_id, 2: list<ConfigValue> values) '''
        return self._client.addConfigInfo(ConnectionManager.run_id, config_list)

    # def add_skip_path(self, path):
    #    ''' bool addSkipPath(1: i64 run_id, 2: list<string> paths) '''
    #    return self._client.addSkipPath(ConnectionManager.run_id, path)

    def add_build_action(self, build_cmd, check_cmd):
        ''' i64  addBuildAction(1: i64 run_id, 2: string build_cmd) '''
        return self._client.addBuildAction(ConnectionManager.run_id,
                                            build_cmd, check_cmd)

    def finish_build_action(self, action_id, failure):
        ''' bool finishBuildAction(1: i64 action_id, 2: string failure) '''
        return self._client.finishBuildAction(action_id, failure)

    def add_report(self, build_action_id, file_id, bug_hash, bug_hash_type,
                   checker_message, bugpath, events, checker_id, checker_cat,
                   bug_type, severity):
        ''' i64  addReport(1: i64 build_action_id, 2: i64 file_id,
            3: string bug_hash, 4: string checker_message, 5: BugPath bugpath,
            6: BugPathEvents events, 7: string checker_id,
            8: string checker_cat, 9: string bug_type,
            10: shared.Severity severity) '''
        return self._client.addReport(build_action_id, file_id, bug_hash,
                                       bug_hash_type, checker_message, bugpath,
                                       events, checker_id, checker_cat,
                                       bug_type, severity)

    def need_file_content(self, filepath):
        ''' NeedFileResult needFileContent(1: i64 run_id, 2: string filepath)
        '''
        return self._client.needFileContent(ConnectionManager.run_id, filepath)

    def add_file_content(self, file_id, file_content):
        ''' bool addFileContent(1: i64 file_id, 2: binary file_content) '''
        return self._client.addFileContent(file_id, file_content)


# -----------------------------------------------------------------------------
class ConnectionManager(object):
    ''' ContextManager class for handling connections.
        Store common information for about connection.
        Start and stop the server.'''
    host = 'localhost'
    port = None
    database_host = 'localhost'
    database_port = 8764
    run_id = None
    _database = None
    _server = None
    run_env = None

    # -------------------------------------------------------------------------
    @classmethod
    def start_postgres(cls, context, init_db=True):
        '''
        init_db : Initialize database locally if possible
        '''

        dbusername = context.db_username

        LOG.info('Checking for database')
        if not database_handler.is_database_running(cls.database_host,
                                                    cls.database_port,
                                                    dbusername, cls.run_env):
            LOG.info('Database is not running yet')
            # On remote host we cannot initialize a new database
            if not util.is_localhost(cls.database_host):
                sys.exit(1)

            db_path = context.database_path
            if init_db:
                if not database_handler.is_database_exist(db_path) and \
                   not database_handler.initialize_database(db_path, dbusername,
                                                            cls.run_env):
                    # The database does not exist and cannot create
                    LOG.error('Database is missing and the initialization '
                              'of a new failed!')
                    LOG.error('Please check your configuration!')
                    sys.exit(1)
            else:
                if not database_handler.is_database_exist(db_path):
                    # The database does not exists
                    LOG.error('Database is missing!')
                    LOG.error('Please check your configuration!')
                    sys.exit(1)

            LOG.info('Starting database')
            cls._database = database_handler.start_database(db_path,
                                                            cls.database_host,
                                                            cls.database_port,
                                                            cls.run_env)
            atexit.register(cls._database.terminate)

    # -------------------------------------------------------------------------
    @classmethod
    def block_until_db_starts(cls, context):
        ''' Wait for database to start if the database was
        started by this client and polling is possible. '''

        tries_count = 0

        while not database_handler.is_database_running(cls.database_host,
                cls.database_port, context.db_username, cls.run_env) and \
                tries_count < 5:
            tries_count += 1
            time.sleep(3)

        if tries_count >= 5 or not cls._database.poll():
            # last chance to start
            if cls._database.returncode is None:
                # it is possible that the database starts really slow
                time.sleep(20)
                if not database_handler.is_database_running(cls.host,
                        cls.database_port, context.db_username, cls.run_env):

                    LOG.error('Failed to start database.')
                    sys.exit(1)

        else:
            LOG.error('Failed to start database server.')
            LOG.error('Database server exit code: '+str(cls._server.returncode))
            sys.exit(1)

    # -------------------------------------------------------------------------
    # Server related methods
    @classmethod
    def start_server(cls, dbname, context, wait_for_start=True):

        cls.start_postgres(context)

        if wait_for_start:
            cls.block_until_db_start_proc_free(context)

        is_server_started = multiprocessing.Event()

        cls._server = multiprocessing.Process(target=report_server.run_server,
                                              args=(
                                              context.db_username,
                                              cls.port, dbname,
                                              cls.database_host,
                                              cls.database_port,
                                              context.db_version_info,
                                              is_server_started))

        cls._server.daemon = True
        cls._server.start()

        if wait_for_start:
            # Wait a bit
            counter = 0
            while not is_server_started.is_set() and counter < 4:
                LOG.debug('Waiting for checker server to start.')
                time.sleep(3)
                counter += 1

            if counter >= 4 or not cls._server.is_alive():
                # last chance to start
                if cls._server.exitcode is None:
                    # it is possible that the database starts really slow
                    time.sleep(5)
                    if not is_server_started.is_set():
                        LOG.error('Failed to start checker server.')
                        sys.exit(1)
                else:
                    LOG.error('Failed to start checker server.')
                    LOG.error('Checker server exit code: ' +
                              str(cls._server.exitcode))
                    sys.exit(1)

        atexit.register(cls._server.terminate)
        LOG.debug('Checker server start sequence done.')

    # -------------------------------------------------------------------------
    @classmethod
    def stop_server(cls):
        # if ConnectionManager._database:
            # ConnectionManager._database.terminate()

        if ConnectionManager._server:
            ConnectionManager._server.terminate()

    # -------------------------------------------------------------------------
    @classmethod
    def block_until_db_start_proc_free(cls, context):
        ''' Wait for database if the database process was stared
        with a different client. No polling is possible.'''

        tries_count = 0
        max_try = 20
        timeout = 5
        while not database_handler.is_database_running(cls.database_host,
                cls.database_port, context.db_username, cls.run_env) and \
                tries_count < max_try:
            tries_count += 1
            time.sleep(timeout)

            if tries_count >= max_try:
                LOG.error('Failed to start database.')
                sys.exit(1)
