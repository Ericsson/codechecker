# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the test package analyze.
"""


import os
import shutil
import pytest

from libtest import env


#global TEST_WORKSPACE
## Test workspace should be initialized in this module.
#TEST_WORKSPACE = None
#
#@pytest.fixture(scope="package", autouse=True)
#def setup_package():
#    """Setup the environment for the tests."""
#
#    TEST_WORKSPACE = env.get_workspace('analyze')
#
#    report_dir = os.path.join(TEST_WORKSPACE, 'reports')
#    os.makedirs(report_dir)
#
#    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE
#    assert False
#
#    yield
#
#    """Delete the workspace associated with this test"""
#
#    print("Removing: " + TEST_WORKSPACE)
#    shutil.rmtree(TEST_WORKSPACE)
