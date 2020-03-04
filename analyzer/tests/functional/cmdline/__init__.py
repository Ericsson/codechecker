# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the test package analyze.
"""


import os
import shutil

from libtest import env


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('cmdline')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE


def teardown_package():
    """Delete the workspace associated with this test"""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)
