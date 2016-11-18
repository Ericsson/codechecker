# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import atexit
import codecs
import contextlib
import multiprocessing
import os
import sys
import time

import shared
from DBThriftAPI import CheckerReport
from DBThriftAPI.ttypes import SuppressBugData
from thrift import Thrift
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket
from thrift.transport import TTransport

from codechecker_lib import suppress_file_handler
from codechecker_lib.logger import LoggerFactory
from storage_server import report_server

LOG = LoggerFactory.get_new_logger('CLIENT')


# -----------------------------------------------------------------------------
def clean_suppress(connection, run_id):
    """
    Clean all the suppress information from the database.
    """
    connection.clean_suppress_data(run_id)


# -----------------------------------------------------------------------------
def send_suppress(run_id, connection, file_name):
    """
    Collect suppress information from the suppress file to be stored
    in the database.
    """
    suppress_data = []
    if os.path.exists(file_name):
        with codecs.open(file_name, 'r', 'UTF-8') as s_file:
            suppress_data = suppress_file_handler.get_suppress_data(s_file)

    if len(suppress_data) > 0:
        connection.add_suppress_bug(run_id, suppress_data)


# -----------------------------------------------------------------------------
def replace_config_in_db(run_id, connection, configs):
    configuration_list = []
    for checker_name, key, key_value in configs:
        configuration_list.append(shared.ttypes.ConfigValue(checker_name,
                                                            key,
                                                            str(key_value)))
    # Store checker configs to the database.
    connection.replace_config_info(run_id, configuration_list)


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def get_connection():
    """ Automatic Connection handler via ContextManager idiom.
        You can use this in with statement."""
    connection = ConnectionManager.instance.create_connection()

    try:
        yield connection
    finally:
        connection.close_connection()


# -----------------------------------------------------------------------------
class Connection(object):
    """ Represent a connection to the server.
        In constructor establish the connection and
        you have to call close_connection function to close it.
        So, you should set it up before create a connection."""

    def __init__(self, host, port):
        """ Establish the connection between client and server. """

        tries_count = 0
        while True:
            try:
                self._transport = TSocket.TSocket(host, port)
                self._transport = TTransport.TBufferedTransport(
                    self._transport)
                self._protocol = TBinaryProtocol.TBinaryProtocol(
                    self._transport)
                self._client = CheckerReport.Client(self._protocol)
                self._transport.open()
                break

            except Thrift.TException as thrift_exc:
                if tries_count > 3:
                    LOG.error('The client cannot establish the connection '
                              'with the server!')
                    LOG.error('%s' % thrift_exc.message)
                    sys.exit(2)
                else:
                    tries_count += 1
                    time.sleep(1)

    def close_connection(self):
        """ Close connection. """
        self._transport.close()

    def add_checker_run(self, command, name, version, force):
        run_id = self._client.addCheckerRun(command, name, version, force)
        return run_id

    def finish_checker_run(self, run_id):
        """ bool finishCheckerRun(1: i64 run_id) """
        self._client.finishCheckerRun(run_id)

    def clean_suppress_data(self, run_id):
        """
        Clean suppress data.
        """
        self._client.cleanSuppressData(run_id)

    def add_suppress_bug(self, run_id, suppress_data):
        """
        Process and send suppress data
        which should be sent to the report server.
        """
        bugs_to_suppress = []
        for checker_hash, file_name, comment in suppress_data:
            comment = comment.encode('UTF-8')
            suppress_bug = SuppressBugData(checker_hash,
                                           file_name,
                                           comment)
            bugs_to_suppress.append(suppress_bug)

        return self._client.addSuppressBug(run_id,
                                           bugs_to_suppress)

    def add_skip_paths(self, run_id, paths):
        """ bool addSkipPath(1: i64 run_id, 2: map<string, string> paths) """
        # convert before sending through thrift
        converted = {}
        for path, comment in paths.items():
            converted[path] = comment.encode('UTF-8')
        return self._client.addSkipPath(run_id, converted)

    def replace_config_info(self, run_id, config_list):
        ''' bool replaceConfigInfo(1: i64 run_id,
                                   2: list<ConfigValue> values)
        '''
        return self._client.replaceConfigInfo(run_id, config_list)

    def add_build_action(self, run_id, build_cmd, check_cmd, analyzer_type,
                         analyzed_source_file):
        """
        i64  addBuildAction(1: i64 run_id, 2: string build_cmd,
                            3: string check_cmd, 4: string analyzer_type,
                            5: string analyzed_source_file)
        """
        return self._client.addBuildAction(run_id,
                                           build_cmd,
                                           check_cmd,
                                           analyzer_type,
                                           analyzed_source_file)

    def finish_build_action(self, action_id, failure):
        """ bool finishBuildAction(1: i64 action_id, 2: string failure) """
        return self._client.finishBuildAction(action_id, failure)

    def add_report(self, build_action_id, file_id, bug_hash,
                   checker_message, bugpath, events, checker_id, checker_cat,
                   bug_type, severity, suppress):
        """  """
        return self._client.addReport(build_action_id, file_id, bug_hash,
                                      checker_message, bugpath,
                                      events, checker_id, checker_cat,
                                      bug_type, severity, suppress)

    def need_file_content(self, run_id, filepath):
        """ NeedFileResult needFileContent(1: i64 run_id, 2: string filepath)
        """
        return self._client.needFileContent(run_id, filepath)

    def add_file_content(self, file_id, file_content):
        """ bool addFileContent(1: i64 file_id, 2: binary file_content) """
        return self._client.addFileContent(file_id, file_content)


# -----------------------------------------------------------------------------
class ConnectionManager(object):
    """
    ContextManager class for handling connections.
    Store common information for about connection.
    Start and stop the server.
    """

    run_id = None

    def __init__(self, database_server, host, port):
        self.database_server = database_server
        self.host = host
        self.port = port
        ConnectionManager.instance = self

    def create_connection(self):
        return Connection(self.host, self.port)

    def start_report_server(self):

        is_server_started = multiprocessing.Event()
        connection_str = self.database_server.get_connection_string()
        server = multiprocessing.Process(target=report_server.run_server,
                                         args=(self.port,
                                               connection_str,
                                               is_server_started))

        server.daemon = True
        server.start()

        # Wait a bit.
        counter = 0
        while not is_server_started.is_set() and counter < 4:
            LOG.debug('Waiting for checker server to start.')
            time.sleep(3)
            counter += 1

        if counter >= 4 or not server.is_alive():
            # Last chance to start.
            if server.exitcode is None:
                # It is possible that the database starts really slow.
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
