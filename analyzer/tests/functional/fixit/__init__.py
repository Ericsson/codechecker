# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the test package fixit.
"""


import os
import shutil

from libtest import env


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('fixit')

    report_dir = os.path.join(TEST_WORKSPACE, 'reports')
    os.makedirs(report_dir)

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE


def teardown_package():
    """Delete the workspace associated with this test"""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)
