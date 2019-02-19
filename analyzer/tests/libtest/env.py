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
    tmp_dir = os.path.join(REPO_ROOT, 'build')
    base_dir = os.path.join(tmp_dir, 'workspace')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    if test_id:
        return tempfile.mkdtemp(prefix=test_id+"-", dir=base_dir)
    else:
        return base_dir
