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
import subprocess
import time

from libtest import codechecker
from libtest import env

# Stopping events for CodeChecker servers.
EVENT_1 = multiprocessing.Event()
EVENT_2 = multiprocessing.Event()

# Test workspace initialized at setup for authentication tests.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('instances')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    test_env = env.test_env(TEST_WORKSPACE)

    # Setup environment variables for the test cases.
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port()}

    codechecker_cfg = {
        'workspace': TEST_WORKSPACE,
        'check_env': test_env,
        'run_names': [],
        'checkers': []
    }
    codechecker_cfg.update(host_port_cfg)
    test_config['codechecker_1'] = codechecker_cfg

    # We need a second server
    codechecker_cfg = {
        'workspace': TEST_WORKSPACE,
        'check_env': test_env,
        'run_names': [],
        'checkers': []
    }
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port()}

    if host_port_cfg['viewer_port'] == \
            test_config['codechecker_1']['viewer_port']:
        host_port_cfg['viewer_port'] = int(host_port_cfg['viewer_port']) + 1

    codechecker_cfg.update(host_port_cfg)
    test_config['codechecker_2'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Wait for previous test instances to terminate properly and
    # clean the instance file in the user's home directory.
    time.sleep(5)


def teardown_package():
    """Stop the CodeChecker server."""

    # Let the remaining CodeChecker servers die.
    EVENT_1.set()
    EVENT_2.set()

    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
