# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the test package detection_status."""

import multiprocessing
import os
import shutil
import subprocess
import time

from libtest import codechecker
from libtest import env

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()

# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing detection_status."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('detection_status')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Configuration options.
    codechecker_cfg = {
        'suppress_file': None,
        'skip_list_file': None,
        'check_env': env.test_env(),
        'workspace': TEST_WORKSPACE,
        'pg_db_config': env.get_postgresql_cfg(),
        'checkers': [],
        'test_project': 'hello'
    }

    # Get new unique port numbers for this test run.
    host_port_cfg = env.get_host_port_cfg()

    # Extend the checker configuration with the port numbers.
    codechecker_cfg.update(host_port_cfg)

    # Start the CodeChecker server.
    print("Starting server to get results")
    _start_server(codechecker_cfg, {}, False)

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, {'codechecker_cfg': codechecker_cfg})


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
    time.sleep(20)
