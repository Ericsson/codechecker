# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the package tests."""

import json
import multiprocessing
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from subprocess import CalledProcessError

from libtest import get_free_port
from libtest import project
from libtest import codechecker
from libtest import env

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()

# Test workspace initialized at setup for authentication tests.
TEST_WORKSPACE = None


def enable_auth(workspace):
    """
    Create a dummy authentication-enabled configuration and
    an auth-enabled server.

    Running the tests only work if the initial value (in package
    session_config.json) is FALSE for authentication.enabled.
    """

    session_config_filename = "session_config.json"

    cc_package = env.codechecker_package()
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
        scfg_dict["authentication"]["method_dictionary"]["auths"] = ["cc:test"]

        json.dump(scfg_dict, scfg, indent=2, sort_keys=True)
        scfg.truncate()


def setup_package():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('authentication')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    clang_version = env.clang_to_test()

    pg_db_config = env.get_postgresql_cfg()

    test_config = {}

    project_info = project.get_info(test_project)

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    # Setup environment varaibled for the test cases.
    host_port_cfg = env.get_host_port_cfg()

    test_env = env.test_env()

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'pg_db_config': pg_db_config,
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)

    codechecker_cfg['run_names'] = []

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Enable authentication and start the CodeChecker server.
    enable_auth(TEST_WORKSPACE)
    print("Starting server to get results")
    _start_server(codechecker_cfg, test_config, False)


def teardown_package():
    """Stop the CodeChecker server."""
    __STOP_SERVER.set()

    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)


def _start_server(codechecker_cfg, test_config, auth=False):
    """Start the CodeChecker server."""
    def start_server_proc(event, server_cmd, checking_env):
        """Target function for starting the CodeChecker server."""
        proc = subprocess.Popen(server_cmd, env=checking_env)

        # Blocking termination until event is set.
        event.wait()

        # If proc is still running, stop it.
        if proc.poll() is None:
            proc.terminate()

    server_cmd = codechecker.serv_cmd(codechecker_cfg, test_config)

    server_proc = multiprocessing.Process(
        name='server',
        target=start_server_proc,
        args=(__STOP_SERVER, server_cmd, codechecker_cfg['check_env']))

    server_proc.start()
    # Wait for server to start and connect to database.
    time.sleep(20)
