# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Setup for the test package report_server_api.  """

from subprocess import CalledProcessError

import multiprocessing
import os
import shutil
import subprocess
import sys
import time
import uuid

from libtest import codechecker
from libtest import env
from libtest import get_free_port
from libtest import project

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()
TEST_WORKSPACE = None


def setup_package():
    """
    Setup the environment for the report_server_api test.
    """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('report_server_api')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project_path = project.path()

    pg_db_config = env.get_postgresql_cfg()

    test_config = {}

    suppress_file = None

    skip_list_file = None

    # Setup env vars for test cases.
    host_port_cfg = env.get_host_port_cfg()

    test_env = env.test_env()

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'use_postgresql': False,
        'workspace': TEST_WORKSPACE,
        'pg_db_config': pg_db_config,
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export test configuration.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Start the CodeChecker server.
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
