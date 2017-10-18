# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import subprocess

from libcodechecker import generic_package_context
from libcodechecker.logger import LoggerFactory
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.analyze import analyzer_env

LOG = LoggerFactory.get_new_logger('HOST CHECK')


def is_ctu_capable():
    """ Detects if the current clang is CTU compatible. """

    context = generic_package_context.get_context()
    ctu_func_map_cmd = context.ctu_func_map_cmd
    try:
        version = subprocess.check_output([ctu_func_map_cmd, '-version'])
    except (subprocess.CalledProcessError, OSError):
        version = 'ERROR'
    return version != 'ERROR'


def is_statistics_capable():
    """ Detects if the current clang is Statistics compatible. """
    context = generic_package_context.get_context()

    analyzer = "clangsa"
    enabled_analyzers = [analyzer]
    cfg_handlers = analyzer_types.build_config_handlers({},
                                                        context,
                                                        enabled_analyzers)

    clangsa_cfg = cfg_handlers[analyzer]
    analyzer = analyzer_types.construct_analyzer_type(analyzer,
                                                      clangsa_cfg,
                                                      None)

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    checkers = analyzer.get_analyzer_checkers(clangsa_cfg, check_env)

    import re
    stat_checkers_pattern = re.compile(r'.+statisticsCollector.+')

    stats_checkers = []
    for checker_name, _ in checkers:
        if stat_checkers_pattern.match(checker_name):
            return True

    return False


def check_zlib():
    """ Check if zlib compression is available.
    If wrong libraries are installed on the host machine it is
    possible the the compression fails which is required to
    store data into the database.
    """

    try:
        import zlib
        zlib.compress('Compress this')
        return True
    except Exception as ex:
        LOG.error(str(ex))
        LOG.error('Failed to import zlib module.')
        return False


def get_postgresql_driver_name():
    try:
        driver = os.getenv('CODECHECKER_DB_DRIVER')
        if driver:
            return driver

        try:
            import psycopg2  # NOQA.
            return "psycopg2"
        except Exception:
            import pg8000  # NOQA.
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
    if check_postgresql:
        try:
            get_postgresql_driver_name()
            return True
        except Exception:
            return False
    else:
        try:
            try:
                import pysqlite2
            except Exception:
                import sqlite3
        except Exception as ex:
            LOG.debug(ex)
            return False
        return True
