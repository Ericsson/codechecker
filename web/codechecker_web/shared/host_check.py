# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Functions to check the host machine and the analyzers for various
features, dependecies and configurations.
"""


import os

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def check_zlib():
    """ Check if zlib compression is available.
    If wrong libraries are installed on the host machine it is
    possible the the compression fails which is required to
    store data into the database.
    """
    try:
        import zlib
        zlib.compress(b'Compress this')
        return True
    except Exception as ex:
        LOG.error(str(ex))
        LOG.error('Failed to import zlib module.')
        return False


def get_postgresql_driver_name():
    # pylint: disable=unused-variable
    try:
        driver = os.getenv('CODECHECKER_DB_DRIVER')
        if driver:
            return driver

        try:
            # pylint: disable=W0611
            import psycopg2
            return "psycopg2"
        except Exception:
            # pylint: disable=W0611
            import pg8000
            return "pg8000"
    except Exception as ex:
        LOG.error(str(ex))
        LOG.error('Failed to import psycopg2 or pg8000 module.')
        raise


def check_postgresql_driver():
    try:
        get_postgresql_driver_name()
        return True
    except Exception as ex:
        LOG.debug(ex)
        return False


def check_sql_driver(check_postgresql):
    # pylint: disable=unused-variable
    if check_postgresql:
        try:
            get_postgresql_driver_name()
            return True
        except Exception:
            return False
    else:
        try:
            try:
                # pylint: disable=W0611
                import pysqlite2
            except Exception:
                # pylint: disable=W0611
                import sqlite3
        except Exception as ex:
            LOG.debug(ex)
            return False
        return True
