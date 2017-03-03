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

# Test workspace used to diff tests.
TEST_WORKSPACE = None


def setup_package():
    """
    Setup the environment for the tests.
    Check the test project twice, then start the server.
    """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('diff')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project_path = project.path()

    clang_version = env.clang_to_test()

    pg_db_config = env.get_postgresql_cfg()

    test_config = {}

    project_info = project.get_info(project.path())

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    # Setup environment variabled for test cases.
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

    test_config['codechecker_cfg'] = codechecker_cfg

    ret = project.clean(test_project_path, test_env)
    if ret:
        sys.exit(ret)

    test_project_name_base = project_info['name'] + '_' + uuid.uuid4().hex

    ret = codechecker.check(codechecker_cfg,
                            test_project_name_base,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("First analysis of the test project was successful.")

    if pg_db_config:
        print("Waiting for PotgreSQL to stop.")
        codechecker.wait_for_postgres_shutdown(TEST_WORKSPACE)

    ret = project.clean(test_project_path, test_env)
    if ret:
        sys.exit(ret)

    test_project_name_new = project_info['name'] + '_' + uuid.uuid4().hex

    ret = codechecker.check(codechecker_cfg,
                            test_project_name_new,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("Second analysis of the test project was successful.")

    if pg_db_config:
        print("Waiting for PotgreSQL to stop.")
        codechecker.wait_for_postgres_shutdown(TEST_WORKSPACE)

    # Order of the test run names matter at comparison!
    codechecker_cfg['run_names'] = [test_project_name_base,
                                    test_project_name_new]

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Start the CodeChecker server.
    print("Starting server to get results")
    _start_server(codechecker_cfg, test_config, False)


def teardown_package():
    """Stop the CodeChecker server."""
    __STOP_SERVER.set()

    # TODO: If environment variable is set keep the workspace
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
    time.sleep(10)
