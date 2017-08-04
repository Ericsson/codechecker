# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""Setup for the test package comment."""

import multiprocessing
import os
import shutil
import subprocess
import sys
import time
import uuid

from libtest import codechecker
from libtest import env
from libtest import project

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()

# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests. """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('comment')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_project_path = project.path(test_project)

    test_config = {}

    project_info = project.get_info(test_project)

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    # Setup environment variables for the test cases.
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port(),
                     'viewer_product': 'comment'}

    test_env = env.test_env()
    test_env['HOME'] = TEST_WORKSPACE

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
        'checkers': ['-d', 'core.CallAndMessage',
                     '-e', 'core.StackAddressEscape']
    }

    codechecker_cfg.update(host_port_cfg)

    # Start the CodeChecker server.
    print("Starting server to get results")
    env.enable_auth(TEST_WORKSPACE)
    _start_server(codechecker_cfg, test_config, False)
    print("server started")
    codechecker.login(codechecker_cfg, TEST_WORKSPACE,
                      "cc",
                      "test")

    # We still need to create a product on the new server, because
    # in PostgreSQL mode, the same database is used for configuration
    # by the newly started instances.
    codechecker.add_test_package_product(host_port_cfg, TEST_WORKSPACE,
                                         test_env)

    # Check the test project for the first time.
    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

    ret = codechecker.check(codechecker_cfg,
                            test_project_name,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("Analyzing test project was succcessful.")

    # Check the test project again.
    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex
    ret = codechecker.check(codechecker_cfg,
                            test_project_name,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("Analyzing test project was successful.")

    codechecker_cfg['run_names'] = [test_project_name]
    test_config['codechecker_cfg'] = codechecker_cfg
    env.export_test_cfg(TEST_WORKSPACE, test_config)


def teardown_package():
    """Stop the CodeChecker server and clean up after the tests."""
    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

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
