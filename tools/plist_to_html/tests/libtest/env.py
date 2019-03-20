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


def test_proj_root():
    return os.path.abspath(os.environ['TEST_PROJ'])


def get_workspace(test_id='test'):
    """ Return a temporary workspace for the tests. """
    workspace_root = os.environ.get("PLIST_TO_HTML_TEST_WORKSPACE_ROOT")
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
