# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Setup for the config test for the web commands. """


import os
import shutil

from libtest import env


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('config')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Create a basic CodeChecker config for the tests, this should
    # be imported by the tests and they should only depend on these
    # configuration options.
    codechecker_cfg = {
        'workspace': TEST_WORKSPACE,
        'check_env': env.test_env(TEST_WORKSPACE),
        'viewer_host': 'localhost',
        'viewer_product': 'db_cleanup'
    }

    env.export_test_cfg(TEST_WORKSPACE, {'codechecker_cfg': codechecker_cfg})


def teardown_package():
    """ Delete the workspace associated with this test. """

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)
