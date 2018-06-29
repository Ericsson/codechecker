# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the package tests."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import multiprocessing
import os
import shutil
import subprocess
import time

from libtest import project
from libtest import codechecker
from libtest import env

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()

# Test workspace initialized at setup for authentication tests.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('authentication')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    # Setup environment variables for the test cases.
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port(),
                     'viewer_product': 'authentication'}

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)

    codechecker_cfg['run_names'] = []

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Enable authentication and start the CodeChecker server.
    env.enable_auth(TEST_WORKSPACE)
    print("Starting server to get results")
    _start_server(codechecker_cfg, test_config, False)


def teardown_package():
    """Stop the CodeChecker server and clean up after the tests."""
    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    # Removing the product through this server requires credentials.
    codechecker_cfg = env.import_test_cfg(TEST_WORKSPACE)['codechecker_cfg']
    codechecker.remove_test_package_product(TEST_WORKSPACE,
                                            codechecker_cfg['check_env'])

    __STOP_SERVER.set()

    # The custom server stated in a separate home needs to be waited, so it
    # can properly execute its finalizers.
    time.sleep(5)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)


# This server uses custom server configuration, which is brought up here
# and torn down by the package itself --- it does not connect to the
# test run's "master" server.
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

    server_cmd = codechecker.serv_cmd(codechecker_cfg['workspace'],
                                      str(codechecker_cfg['viewer_port']),
                                      env.get_postgresql_cfg())

    server_proc = multiprocessing.Process(
        name='server',
        target=start_server_proc,
        args=(__STOP_SERVER, server_cmd, codechecker_cfg['check_env']))

    server_proc.start()

    # Wait for server to start and connect to database.
    time.sleep(20)
