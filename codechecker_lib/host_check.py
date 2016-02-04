# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import errno
import subprocess
import os

from codechecker_lib import logger

LOG = logger.get_new_logger('HOST CHECK')


# -----------------------------------------------------------------------------
def check_zlib():
    ''' Check if zlib compression is available
    if wrong libraries are installed on the host machine it is
    possible the the compression failes which is required to
    store data into the database.
    '''

    try:
        import zlib
        return True
    except Exception as ex:
        LOG.error(str(ex))
        LOG.error('Failed to import zlib module')
        return False

    try:
        zlib.compress('Compress this')
        return True
    except Exception as ex:
        LOG.error(str(ex))
        LOG.error('Zlib copression error', zlib.Z_BEST_COMPRESSION)
        return False

# -----------------------------------------------------------------------------
def get_postgresql_driver_name():
    try:
        driver = os.getenv('CODECHECKER_DB_DRIVER')
        if driver:
            return driver

        try:
            import psycopg2  # NOQA
            return "psycopg2"
        except Exception:
            import pg8000  # NOQA
            return "pg8000"
    except Exception as ex:
        LOG.error(str(ex))
        LOG.error('Failed to import psycopg2 or pg8000 module.')
        raise


# -----------------------------------------------------------------------------
def check_postgresql_driver():
    try:
        get_postgresql_driver_name()
        return True
    except Exception as ex:
        return False


# -----------------------------------------------------------------------------
def check_sql_driver(check_postgresql):
    if check_postgresql:
        try:
            get_postgresql_driver_name()
            return True
        except Exception as ex:
            return False
    else:
        try:
            try:
                import pysqlite2
            except Exception as ex:
                import sqlite3
        except Exception as ex:
            return False
        return True

# -----------------------------------------------------------------------------
def check_clang(compiler_bin, env):
    '''
    simple check if clang is available
    '''
    clang_version_cmd = [compiler_bin, '--version']
    try:
        res = subprocess.call(clang_version_cmd,
                              env=env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if not res:
            return True
        else:
            LOG.error('Failed to run: "' + ' '.join(clang_version_cmd) + '"')
            return False

    except OSError as oerr:
        if oerr[0] == errno.ENOENT:
            LOG.error(oerr)
            LOG.error('Failed to run: ' + ' '.join(clang_version_cmd) + '"')
            return False
