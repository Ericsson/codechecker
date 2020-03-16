# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
""" Setup for the test package analyze. """

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import shutil
import tempfile


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def get_workspace(test_id='test'):
    """ Return a temporary workspace for the tests. """
    workspace_root = os.environ.get("CC_REPORT_HASH_TEST_WORKSPACE_ROOT")
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


def setup_package():
    """ Setup the environment for the tests. """

    global TEST_WORKSPACE
    TEST_WORKSPACE = get_workspace('codechecker_report_hash')

    print(TEST_WORKSPACE)
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE


def teardown_package():
    """ Delete the workspace associated with this test. """

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    # shutil.rmtree(TEST_WORKSPACE)
