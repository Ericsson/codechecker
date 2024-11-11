# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Setup for the test package analyze. """

import os
import shutil
import tempfile


def get_workspace(test_id='test'):
    """ Return a temporary workspace for the tests. """
    workspace_root = os.environ.get("STATISTICS_COLLECTOR_TEST_WORKSPACE_ROOT")
    if not workspace_root:
        # if no external workspace is set create under the build dir
        workspace_root = os.path.join(os.environ['REPO_ROOT'], 'build',
                                      'workspace')

    if not os.path.exists(workspace_root):
        os.makedirs(workspace_root)

    if test_id:
        return tempfile.mkdtemp(prefix=test_id + "-", dir=workspace_root)
    else:
        return workspace_root


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """ Setup the environment for the tests. """

    global TEST_WORKSPACE
    TEST_WORKSPACE = get_workspace('statistics_collector')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE


def teardown_package():
    """ Delete the workspace associated with this test. """

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)
