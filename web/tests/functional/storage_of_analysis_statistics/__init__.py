# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the package tests."""


import multiprocessing
import os
import shutil
import time

from libtest import codechecker
from libtest import env

# Stopping event for CodeChecker server.
EVENT_1 = multiprocessing.Event()

# Test workspace initialized at setup for authentication tests.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('storage_of_analysis_statistics')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    # Setup environment variables for the test cases.
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port(),
                     'viewer_product': 'storage_of_analysis_statistics'}

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'viewer_product': 'storage_of_analysis_statistics',
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports')
    }

    codechecker_cfg.update(host_port_cfg)

    codechecker_cfg['run_names'] = []

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Enable storage of analysis statistics and start the CodeChecker server.
    env.enable_storage_of_analysis_statistics(TEST_WORKSPACE)
    print("Starting server to get results")
    server_access = codechecker.start_server(codechecker_cfg, EVENT_1)

    server_access['viewer_product'] = codechecker_cfg['viewer_product']
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)


def teardown_package():
    """Stop the CodeChecker server and clean up after the tests."""

    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    # Let the remaining CodeChecker servers die.
    EVENT_1.set()

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
