# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import json
import tempfile
import shutil
import socket
import subprocess
import sys

from thrift_client_to_db import get_auth_client
from thrift_client_to_db import get_product_client
from thrift_client_to_db import get_viewer_client

from functional import PKG_ROOT
from functional import REPO_ROOT


def get_free_port():
    """
    Get a free port from the OS.
    """
    # TODO: Prone to errors if the OS assigns port to someone else before use.

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()

    return free_port


def get_postgresql_cfg():
    """
    Returns PostgreSQL config if should be used based on the environment
    settings if not return none.
    """
    use_postgresql = os.environ.get('TEST_USE_POSTGRESQL', '') == 'true'
    if use_postgresql:
        pg_db_config = {'dbaddress': 'localhost',
                        'dbport': os.environ.get('TEST_DBPORT'),
                        'dbname': 'codechecker_config'
                        }
        if os.environ.get('TEST_DBUSERNAME', False):
            pg_db_config['dbusername'] = os.environ['TEST_DBUSERNAME']
        return pg_db_config
    else:
        return None


def add_database(dbname, env=None):
    """
    Creates a new database with a given name.
    This has no effect outside PostgreSQL mode. (SQLite databases are
    created automatically by Python.)
    """

    pg_config = get_postgresql_cfg()
    if pg_config:
        pg_config['dbname'] = dbname

        psql_command = ['psql',
                        '-h', pg_config['dbaddress'],
                        '-p', str(pg_config['dbport']),
                        '-d', 'postgres',
                        '-c', "CREATE DATABASE \"" + pg_config['dbname'] + "\""
                        ]
        if 'dbusername' in pg_config:
            psql_command += ['-U', pg_config['dbusername']]

        print(psql_command)
        subprocess.call(psql_command, env=env)


def del_database(dbname, env=None):
    """
    Deletes the given database.
    This has no effect outside PostgreSQL mode.
    """

    pg_config = get_postgresql_cfg()
    if pg_config:
        pg_config['dbname'] = dbname

        psql_command = ['psql',
                        '-h', pg_config['dbaddress'],
                        '-p', str(pg_config['dbport']),
                        '-d', 'postgres',
                        '-c', "DROP DATABASE \"" + pg_config['dbname'] + "\""]
        if 'dbusername' in pg_config:
            psql_command += ['-U', pg_config['dbusername']]

        print(psql_command)
        subprocess.call(psql_command, env=env)


def clang_to_test():
    return "clang_"+os.environ.get('TEST_CLANG_VERSION', 'stable')


def setup_viewer_client(workspace,
                        endpoint='/CodeCheckerService',
                        auto_handle_connection=True,
                        session_token=None):
    # Read port and host from the test config file.
    codechecker_cfg = import_test_cfg(workspace)['codechecker_cfg']
    port = codechecker_cfg['viewer_port']
    host = codechecker_cfg['viewer_host']
    product = codechecker_cfg['viewer_product']

    return get_viewer_client(host=host,
                             port=port,
                             product=product,
                             endpoint=endpoint,
                             auto_handle_connection=auto_handle_connection,
                             session_token=session_token)


def setup_auth_client(workspace,
                      uri='/Authentication',
                      auto_handle_connection=True,
                      session_token=None):

    codechecker_cfg = import_test_cfg(workspace)['codechecker_cfg']
    port = codechecker_cfg['viewer_port']
    host = codechecker_cfg['viewer_host']

    return get_auth_client(port=port,
                           host=host,
                           uri=uri,
                           auto_handle_connection=auto_handle_connection,
                           session_token=session_token)


def setup_product_client(workspace,
                         uri='/Products',
                         auto_handle_connection=True,
                         session_token=None):

    codechecker_cfg = import_test_cfg(workspace)['codechecker_cfg']
    port = codechecker_cfg['viewer_port']
    host = codechecker_cfg['viewer_host']

    return get_product_client(port=port,
                              host=host,
                              uri=uri,
                              auto_handle_connection=auto_handle_connection,
                              session_token=session_token)


def repository_root():
    return os.path.abspath(os.environ['REPO_ROOT'])


def test_proj_root():
    return os.path.abspath(os.environ['TEST_PROJ'])


def setup_test_proj_cfg(workspace):
    return import_test_cfg(workspace)['test_project']


def import_codechecker_cfg(workspace):
    return import_test_cfg(workspace)['codechecker_cfg']


def get_run_names(workspace):
    return import_test_cfg(workspace)['codechecker_cfg']['run_names']


def parts_to_url(codechecker_cfg):
    """
    Creates a product URL string from the test configuration dict.
    """
    return codechecker_cfg['viewer_host'] + ':' + \
        str(codechecker_cfg['viewer_port']) + '/' + \
        codechecker_cfg['viewer_product']


def get_workspace(test_id='test'):
    tmp_dir = os.path.join(REPO_ROOT, 'build')
    base_dir = os.path.join(tmp_dir, 'workspace')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    if test_id:
        return tempfile.mkdtemp(prefix=test_id+"-", dir=base_dir)
    else:
        return base_dir


def clean_wp(workspace):
    if os.path.exists(workspace):
        print("Removing workspace:" + workspace)
        shutil.rmtree(workspace)
    os.makedirs(workspace)


def import_test_cfg(workspace):
    cfg_file = os.path.join(workspace, "test_config.json")
    test_cfg = {}
    with open(cfg_file, 'r') as cfg:
        test_cfg = json.loads(cfg.read())
    return test_cfg


def export_test_cfg(workspace, test_cfg):
    cfg_file = os.path.join(workspace, "test_config.json")
    with open(cfg_file, 'w') as cfg:
        cfg.write(json.dumps(test_cfg, sort_keys=True, indent=2))


def codechecker_cmd():
    return os.path.join(PKG_ROOT, 'bin', 'CodeChecker')


def codechecker_package():
    return PKG_ROOT


def codechecker_env():
    checker_env = os.environ.copy()
    cc_bin = os.path.join(codechecker_package(), 'bin')
    checker_env['PATH'] = cc_bin + ":" + checker_env['PATH']
    return checker_env


def test_env():
    base_env = os.environ.copy()
    base_env['PATH'] = os.path.join(codechecker_package(), 'bin') + \
        ':' + base_env['PATH']
    return base_env


def enable_auth(workspace):
    """
    Create a dummy authentication-enabled configuration and
    an auth-enabled server.

    Running the tests only work if the initial value (in package
    session_config.json) is FALSE for authentication.enabled.
    """

    session_config_filename = "session_config.json"

    cc_package = codechecker_package()
    original_auth_cfg = os.path.join(cc_package,
                                     'config',
                                     session_config_filename)

    shutil.copy(original_auth_cfg, workspace)

    session_cfg_file = os.path.join(workspace,
                                    session_config_filename)

    with open(session_cfg_file, 'r+') as scfg:
        __scfg_original = scfg.read()
        scfg.seek(0)
        try:
            scfg_dict = json.loads(__scfg_original)
        except ValueError as verr:
            print(verr)
            print('Malformed session config json.')
            sys.exit(1)

        scfg_dict["authentication"]["enabled"] = True
        scfg_dict["authentication"]["method_dictionary"]["enabled"] = True
        scfg_dict["authentication"]["method_dictionary"]["auths"] =\
            ["cc:test", "john:doe"]

        json.dump(scfg_dict, scfg, indent=2, sort_keys=True)
        scfg.truncate()
