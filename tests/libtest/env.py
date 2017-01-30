# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import json
import tempfile
import shutil

from . import get_free_port
from thrift_client_to_db import get_viewer_client
from thrift_client_to_db import get_server_client
from thrift_client_to_db import get_auth_client

from functional import PKG_ROOT
from functional import REPO_ROOT


def get_postgresql_cfg():
    """
    Returns PostgreSQL config if should be used based on the environment
    settings if not return none.
    """
    use_postgresql = os.environ.get('TEST_USE_POSTGRESQL', '') == 'true'
    if use_postgresql:
        pg_db_config = {}
        pg_db_config['dbaddress'] = 'localhost'
        pg_db_config['dbname'] = 'testDb'
        pg_db_config['dbport'] = os.environ.get('TEST_DBPORT', get_free_port())
        if os.environ.get('TEST_DBUSERNAME', False):
            pg_db_config['dbusername'] = os.environ['TEST_DBUSERNAME']
        return pg_db_config
    else:
        return None


def get_host_port_cfg():

    test_config = {
        'server_port': get_free_port(),
        'server_host': 'localhost',
        'viewer_port': get_free_port(),
        'viewer_host': 'localhost',
    }
    return test_config


def clang_to_test():
    return "clang_"+os.environ.get('TEST_CLANG_VERSION', 'stable')


def setup_viewer_client(workspace,
                        uri='/',
                        auto_handle_connection=True,
                        session_token=None):
    # read port and host from the test config file
    port = import_test_cfg(workspace)['codechecker_cfg']['viewer_port']
    host = import_test_cfg(workspace)['codechecker_cfg']['viewer_host']

    return get_viewer_client(port=port,
                             host=host,
                             uri=uri,
                             auto_handle_connection=auto_handle_connection,
                             session_token=session_token)


def setup_server_client(workspace):
    port = import_test_cfg(workspace)['codechecker_cfg']['server_port']
    host = import_test_cfg(workspace)['codechecker_cfg']['server_host']
    return get_server_client(port, host)


def setup_auth_client(workspace,
                      uri='/Authentication',
                      auto_handle_connection=True,
                      session_token=None):

    port = import_test_cfg(workspace)['codechecker_cfg']['viewer_port']
    host = import_test_cfg(workspace)['codechecker_cfg']['viewer_host']

    return get_auth_client(port=port,
                           host=host,
                           uri=uri,
                           auto_handle_connection=auto_handle_connection,
                           session_token=session_token)


def repository_root():
    return os.path.abspath(os.environ['REPO_ROOT'])


def setup_test_proj_cfg(workspace):
    return import_test_cfg(workspace)['test_project']


def import_codechecker_cfg(workspace):
    return import_test_cfg(workspace)['codechecker_cfg']


def get_run_names(workspace):
    return import_test_cfg(workspace)['codechecker_cfg']['run_names']


def get_workspace(test_id='test'):
    tmp_dir = os.path.join(REPO_ROOT, 'build')
    base_dir = os.path.join(tmp_dir, 'workspace')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    return tempfile.mkdtemp(prefix=test_id+"-", dir=base_dir)


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
