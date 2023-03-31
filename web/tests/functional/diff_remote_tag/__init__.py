# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Setup for the test package diff_local_remote_tag.
We store 3 different tags onto the same run name (as of writing this comment).
However, only 2 tags are stored within this file.
"""


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
    """Setup the environment for testing diff_remote_tag."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('diff_remote_tag')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

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
        'checkers': [],
        'trim_path_prefix': TEST_WORKSPACE,
        'analyzers': ['clangsa']
    }

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'diff_remote_tag'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Base analysis ===========================================================

    altered_file = os.path.join(test_proj_path_base, "call_and_message.cpp")
    project.insert_suppression(altered_file)
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_base,
                                                'reports')
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_base)
    if ret:
        sys.exit(1)
    print('Analyzing base was successful.')

    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

    # New analysis ============================================================
    altered_file = os.path.join(test_proj_path_new, "call_and_message.cpp")
    project.insert_suppression(altered_file)
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_new,
                                                'reports')
    codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                   '-e', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_new)
    if ret:
        sys.exit(1)
    print('Analyzing new was successful.')

    # Order of the test run names matter at comparison!
    codechecker_cfg['run_names'] = [test_project_name]

    test_config['test_project'] = project_info
    test_config['codechecker_cfg'] = codechecker_cfg

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # teardown_package() removes these anyways, and we need them in the test.
    # shutil.rmtree(test_proj_path_base, ignore_errors=True)
    # shutil.rmtree(test_proj_path_new, ignore_errors=True)


def teardown_package():
    """Clean up after the test."""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
