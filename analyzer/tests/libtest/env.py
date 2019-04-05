# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test environment setup and configuration helpers.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import tempfile

from functional import PKG_ROOT
from functional import REPO_ROOT


def codechecker_env():
    checker_env = os.environ.copy()
    cc_bin = os.path.join(PKG_ROOT, 'bin')
    checker_env['PATH'] = cc_bin + ":" + checker_env['PATH']
    return checker_env


def test_proj_root():
    return os.path.abspath(os.environ['TEST_PROJ'])


def codechecker_cmd():
    return os.path.join(PKG_ROOT, 'bin', 'CodeChecker')


def get_workspace(test_id='test'):
    """ return a temporary workspace for the tests """
    workspace_root = os.environ.get("CC_TEST_WORKSPACE_ROOT")
    if not workspace_root:
        # if no external workspace is set create under the build dir
        workspace_root = os.path.join(REPO_ROOT, 'build', 'workspace')

    if not os.path.exists(workspace_root):
        os.makedirs(workspace_root)

    if test_id:
        return tempfile.mkdtemp(prefix=test_id+"-", dir=workspace_root)
    else:
        return workspace_root
