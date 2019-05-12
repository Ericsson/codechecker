# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup part for the test package diff_local. """

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import shutil
import sys
import uuid

from libtest import codechecker
from libtest import env
from libtest import project


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing diff_local."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('diff_local')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    # Get the clang version which is used for testing.
    # Important because different clang releases might
    # find different errors.
    clang_version = env.clang_to_test()

    test_config = {}

    test_project = 'cpp'

    project_info = project.get_info(test_project)

    # Copy the test project to the workspace. The tests should
    # work only on this test project.
    test_proj_path_base = os.path.join(TEST_WORKSPACE, "test_proj_base")
    shutil.copytree(project.path(test_project), test_proj_path_base)

    # Copy the test project to the workspace. The tests should
    # work only on this test project.
    test_proj_path_new = os.path.join(TEST_WORKSPACE, "test_proj_new")
    shutil.copytree(project.path(test_project), test_proj_path_new)

    project_info['project_path_base'] = test_proj_path_base
    project_info['project_path_new'] = test_proj_path_new

    test_config['test_project'] = project_info

    # Suppress file should be set here if needed by the tests.
    suppress_file = None

    # Skip list file should be set here if needed by the tests.
    skip_list_file = None

    # Get an environment which should be used by the tests.
    test_env = env.test_env(TEST_WORKSPACE)

    # Create a basic CodeChecker config for the tests, this should
    # be imported by the tests and they should only depend on these
    # configuration options.
    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': []
    }

    # Base analysis
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_base,
                                                'reports')
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_base)
    if ret:
        sys.exit(1)

    # New analysis
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_new,
                                                'reports')
    codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                   '-e', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_new)
    if ret:
        sys.exit(1)

    codechecker_cfg['reportdir_base'] = os.path.join(test_proj_path_base,
                                                     'reports')
    codechecker_cfg['reportdir_new'] = os.path.join(test_proj_path_new,
                                                    'reports')
    test_config['codechecker_cfg'] = codechecker_cfg

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, test_config)


def teardown_package():
    """Clean up after the test."""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)
