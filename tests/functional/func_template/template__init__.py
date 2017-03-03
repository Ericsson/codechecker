# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the test package $TEST_NAME$.

WARNING!!!
This is a generated test skeleton remove the parts not required by the tests.
WARNING!!!

"""

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

# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing $TEST_NAME$."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('$TEST_NAME$')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Get the clang version which is used for testing.
    # Important because different clang releases might
    # find different errors.
    clang_version = env.clang_to_test()

    # PostgreSQL configuration might be empty if tests are run
    # with SQLite.
    pg_db_config = env.get_postgresql_cfg()

    test_config = {}

    project_info = project.get_info(project.path())

    # Copy the test project to the workspace. The tests should
    # work only on this test project.
    test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
    shutil.copytree(project.path(), test_proj_path)

    project_info['project_path'] = test_proj_path

    # Generate a unique name for this test run.
    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

    test_config['test_project'] = project_info

    # Suppress file should be set here if needed by the tests.
    suppress_file = None

    # Skip list file should be set here if needed by the tests.
    skip_list_file = None

    # Get an environment which should be used by the tests.
    test_env = env.test_env()

    # Create a basic CodeChecker config for the tests, this should
    # be imported by the tests and they should only depend on these
    # configuration options.
    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'pg_db_config': pg_db_config,
        'checkers': []
    }

    # Get new unique port numbers for this test run.
    host_port_cfg = env.get_host_port_cfg()

    # Extend the checker configuration with the port numbers.
    codechecker_cfg.update(host_port_cfg)

    # Clean the test project, if needed by the tests.
    ret = project.clean(project.path())
    if ret:
        sys.exit(ret)

    # Check the test project, if needed by the tests.
    ret = codechecker.check(codechecker_cfg,
                            test_project_name,
                            project.path())
    if ret:
        sys.exit(1)
    print("Analyzing the test project was successful.")

    if pg_db_config:
        print("Waiting for PostgreSQL to stop.")
        codechecker.wait_for_postgres_shutdown(TEST_WORKSPACE)

    # Save the run names in the configuration.
    codechecker_cfg['run_names'] = [test_project_name]

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export the test configuration to the workspace.
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
    time.sleep(20)
