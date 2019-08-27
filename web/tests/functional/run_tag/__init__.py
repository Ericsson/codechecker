# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the test package detection_status."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import shutil

from libtest import codechecker
from libtest import env

# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing detection_status."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('run_tag')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Configuration options.
    codechecker_cfg = {
        'suppress_file': None,
        'skip_list_file': None,
        'check_env': env.test_env(TEST_WORKSPACE),
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
        'test_project': 'test_run_tag',
        'analyzers': ['clangsa', 'clang-tidy']
    }

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'run_tag'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, {'codechecker_cfg': codechecker_cfg})


def teardown_package():
    """Clean up after the test."""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)
