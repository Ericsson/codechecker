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
    TEST_WORKSPACE = env.get_workspace('ssl')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    tls_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tls')
    cert_file = os.path.join(tls_dir, 'cert.pem')
    key_file = os.path.join(tls_dir, 'key.pem')

    # Enable SSL
    shutil.copy(cert_file, TEST_WORKSPACE)
    shutil.copy(key_file, TEST_WORKSPACE)

    cacert_file = os.path.join(TEST_WORKSPACE, 'cert.pem')

    # Setup environment variables for the test cases.
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port(),
                     'viewer_product': 'ssl',
                     'viewer_cacert': cacert_file}

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)
    test_config['codechecker_cfg'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Enable authentication and start the CodeChecker server.
    env.enable_auth(TEST_WORKSPACE)
    print("Starting server to get results")
    codechecker.start_server(codechecker_cfg, __STOP_SERVER)


def teardown_package():
    """Stop the CodeChecker server and clean up after the tests."""
    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE
    __STOP_SERVER.set()

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
