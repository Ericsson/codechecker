# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
'''
handle postgres database initialzation and start if required
'''
import os
import subprocess

from codechecker_lib import logger

LOG = logger.get_new_logger('DB_HANDLER')


# -----------------------------------------------------------------------------
def call_command(command, run_env=None):
    ''' Call an external command and return with (output, return_code).'''
    try:
        proc = subprocess.Popen(command, bufsize=-1, env=run_env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        stdout = proc.communicate()[0]
        LOG.debug(stdout)
        return stdout, proc.returncode
    except OSError as oex:
        LOG.error('Running command "' + ' '.join(command) + '" Failed')
        LOG.error(str(oex))
        return '', 1


# -----------------------------------------------------------------------------
def is_database_exist(path):
    ''' Check the postgres instance existence in a given path.'''
    path = path.strip()
    LOG.debug('Checking for database at ' + path)

    return os.path.exists(path) and \
        os.path.exists(os.path.join(path, 'PG_VERSION')) and \
        os.path.exists(os.path.join(path, 'base'))


# -----------------------------------------------------------------------------
def is_database_running(host, port, dbusername, analyzer_env=None):
    ''' Is there postgres instance running on a given host and port.'''
    LOG.debug('Checking if database is running at ' + host + ':' + str(port))

    check_db = ['psql', '-U', dbusername, '-l', '-p', str(port), '-h', host]
    err, code = call_command(check_db, analyzer_env)
    return code == 0


# -----------------------------------------------------------------------------
def initialize_database(path, db_username, analyzer_env=None):
    ''' Initalize a postgres instance with initdb. '''
    LOG.debug('Initializing database at ' + path)

    init_db = ['initdb', '-U', db_username, '-D', path, '-E SQL_ASCII']

    err, code = call_command(init_db, analyzer_env)
    # logger -> print error
    return code == 0


# -----------------------------------------------------------------------------
def start_database(path, host, port, analyzer_env=None):
    ''' Start a postgres instance with given path, host and port.
        Return with process instance. '''
    LOG.debug('Starting database at ' + host + ':' + str(port) + ' ' + path)
    devnull = open(os.devnull, 'wb')

    proc = subprocess.Popen(['postgres', '-i', '-D', path,
                             '-p', str(port), '-h', host],
                            bufsize=-1, env=analyzer_env,
                            stdout=devnull, stderr=subprocess.STDOUT)
    return proc
