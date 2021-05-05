# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import os
import shutil

from libtest import env


TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing db_cleanup."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('db_cleanup')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Create a basic CodeChecker config for the tests, this should
    # be imported by the tests and they should only depend on these
    # configuration options.
    codechecker_cfg = {
        'suppress_file': None,
        'skip_list_file': None,
        'check_env': env.test_env(TEST_WORKSPACE),
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'viewer_host': 'localhost',
        'viewer_product': 'db_cleanup',
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports')
    }

    env.export_test_cfg(TEST_WORKSPACE, {'codechecker_cfg': codechecker_cfg})


def teardown_package():
    """Clean up after the test."""

    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
