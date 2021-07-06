# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the package tests."""


import os
import shutil

from libtest import codechecker
from libtest import env
from libtest import plist_test

# Test workspace initialized at setup for report storage tests.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('store_test')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Configuration options.
    codechecker_cfg = {
        'check_env': env.test_env(TEST_WORKSPACE),
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
        'test_project': 'store_test'
    }

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'store_test'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, {'codechecker_cfg': codechecker_cfg})

    # Copy test files to a temporary directory not to modify the
    # files in the repository.
    # Report files will be overwritten during the tests.
    test_dir = os.path.dirname(os.path.realpath(__file__))
    dst_dir = os.path.join(TEST_WORKSPACE, "test_proj")
    shutil.copytree(os.path.join(test_dir, "test_proj"), dst_dir)

    report_file = os.path.join(dst_dir, "divide_zero.plist")
    plist_test.prefix_file_path(report_file, dst_dir)


def teardown_package():
    """Clean up after the test."""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
