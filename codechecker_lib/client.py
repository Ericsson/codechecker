import re
import sys
import zlib
import time
import atexit
import contextlib
import multiprocessing
import os
import codecs
import ntpath

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
from codechecker_lib import suppress_handler

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
        LOG.debug('Bug hash: ' + bug_hash)

        severity_name = severity_map.get(bug.checker_name, 'UNSPECIFIED')
        severity = shared.ttypes.Severity._NAMES_TO_VALUES[severity_name]

        suppress = False

        source_file = bug.file_path
        last_bug_event = bug.events()[-1]
        bug_line = last_bug_event.start_pos.line

        LOG.debug('Checking source for suppress comment')
        sp_handler = suppress_handler.SourceSuppressHandler(source_file,
                                                            bug_line)
        LOG.debug(source_file)
        LOG.debug(bug_line)
        LOG.debug(bug.checker_name)
        # check for suppress comment
        supp = sp_handler.check_source_suppress()
        if supp:
            # something shoud be suppressed
            suppress_checkers = sp_handler.suppressed_checkers()

            if bug.checker_name in suppress_checkers or \
               suppress_checkers == ['all']:
                suppress = True

                file_path, file_name = ntpath.split(source_file)

                # checker_hash, file_name, comment
                to_suppress = (bug_hash,
                               file_name,
                               sp_handler.suppress_comment())

                LOG.debug(to_suppress)

                connection.add_suppress_bug([to_suppress])

        report_id = connection.add_report(build_action_id,
                                          file_ids[bug.file_path],
                                          bug_hash,
                                          bug.msg,
                                          bug_paths,
                                          bug_events,
                                          bug.checker_name,
                                          bug.category,
                                          bug.type,
                                          severity,
                                          suppress)

        report_ids.append(report_id)


# -----------------------------------------------------------------------------
def clean_suppress(connection, run_id):
    """
    clean all the suppress information from the database
    """
    connection.clean_suppress_data(run_id)


# -----------------------------------------------------------------------------
def send_suppress(connection, file_name):
    """
    collect suppress information from the suppress file to be stored
    in the database
    """
    suppress_data = []
    if os.path.exists(file_name):
        with codecs.open(file_name, 'r', 'UTF-8') as s_file:
            suppress_data = suppress_file_handler.get_suppress_data(s_file)

    if len(suppress_data) > 0:
        connection.add_suppress_bug(suppress_data)

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
    connection = ConnectionManager.instance.create_connection()

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

    def __init__(self, host, port):
        ''' Establish the connection beetwen client and server. '''

        tries_count = 0
        while True:
            try:
                self._transport = TSocket.TSocket(host, port)
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

    def clean_suppress_data(self, run_id):
        """
        clean suppress data
        """
        self._client.cleanSuppressData(run_id)

    def add_suppress_bug(self, suppress_data):
        """
        process and send suppress data
        which should be sent to the report server
        """
        bugs_to_suppress = []
        for checker_hash, file_name, comment in suppress_data:
            comment = comment.encode('UTF-8')
            suppress_bug = SuppressBugData(checker_hash,
                                           file_name,
                                           comment)
            bugs_to_suppress.append(suppress_bug)

        return self._client.addSuppressBug(ConnectionManager.run_id,
                                           bugs_to_suppress)

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

    def add_build_action(self, build_cmd, check_cmd):
        ''' i64  addBuildAction(1: i64 run_id, 2: string build_cmd) '''
        return self._client.addBuildAction(ConnectionManager.run_id,
                                            build_cmd, check_cmd)

    def finish_build_action(self, action_id, failure):
        ''' bool finishBuildAction(1: i64 action_id, 2: string failure) '''
        return self._client.finishBuildAction(action_id, failure)

    def add_report(self, build_action_id, file_id, bug_hash,
                   checker_message, bugpath, events, checker_id, checker_cat,
                   bug_type, severity, suppress):
        '''  '''
        return self._client.addReport(build_action_id, file_id, bug_hash,
                                      checker_message, bugpath,
                                      events, checker_id, checker_cat,
                                      bug_type, severity, suppress)

    def need_file_content(self, filepath):
        ''' NeedFileResult needFileContent(1: i64 run_id, 2: string filepath)
        '''
        return self._client.needFileContent(ConnectionManager.run_id, filepath)

    def add_file_content(self, file_id, file_content):
        ''' bool addFileContent(1: i64 file_id, 2: binary file_content) '''
        return self._client.addFileContent(file_id, file_content)


# -----------------------------------------------------------------------------
class ConnectionManager(object):
    '''
    ContextManager class for handling connections.
    Store common information for about connection.
    Start and stop the server.
    '''

    run_id = None

    def __init__(self, database_server, host, port):
        self.database_server = database_server
        self.host = host
        self.port = port
        ConnectionManager.instance = self

    def create_connection(self):
        return Connection(self.host, self.port)

    def start_report_server(self, db_version_info):

        is_server_started = multiprocessing.Event()
        server = multiprocessing.Process(target=report_server.run_server,
                                         args=(
                                         self.port,
                                         self.database_server.get_connection_string(),
                                         db_version_info,
                                         is_server_started))

        server.daemon = True
        server.start()

        # Wait a bit
        counter = 0
        while not is_server_started.is_set() and counter < 4:
            LOG.debug('Waiting for checker server to start.')
            time.sleep(3)
            counter += 1

        if counter >= 4 or not server.is_alive():
            # last chance to start
            if server.exitcode is None:
                # it is possible that the database starts really slow
                time.sleep(5)
                if not is_server_started.is_set():
                    LOG.error('Failed to start checker server.')
                    sys.exit(1)
            else:
                LOG.error('Failed to start checker server.')
                LOG.error('Checker server exit code: ' +
                          str(server.exitcode))
                sys.exit(1)

        atexit.register(server.terminate)
        self.server = server

        LOG.debug('Checker server start sequence done.')
