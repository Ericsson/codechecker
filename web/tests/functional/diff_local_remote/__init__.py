# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the test package diff_local_remote."""


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
    """Setup the environment for testing diff_local_remote."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('diff_local_remote')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    test_project = 'cpp'

    project_info = project.get_info(test_project)

    # Copy the test project to the workspace. The tests should
    # work only on this test project.
    test_proj_path_local = os.path.join(TEST_WORKSPACE, "test_proj_local")
    shutil.copytree(project.path(test_project), test_proj_path_local)

    # Copy the test project to the workspace. The tests should
    # work only on this test project.
    test_proj_path_remote = os.path.join(TEST_WORKSPACE, "test_proj_remote")
    shutil.copytree(project.path(test_project), test_proj_path_remote)

    project_info['project_path_local'] = test_proj_path_local
    project_info['project_path_remote'] = test_proj_path_remote

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

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'diff_local_remote'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Analyze local, these reports will not be stored to the server.
    altered_file = os.path.join(test_proj_path_local, "call_and_message.cpp")
    project.insert_suppression(altered_file)

    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_local,
                                                'reports')
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_local)
    if ret:
        sys.exit(1)
    print('Analyzing local was successful.')

    # Store results to the remote server.
    test_project_name_remote = project_info['name'] + '_' + uuid.uuid4().hex
    ret = codechecker.store(codechecker_cfg, test_project_name_remote)
    if ret:
        sys.exit(1)

    # Remote analysis, results will be stored to the remote server.
    altered_file = os.path.join(test_proj_path_local, "call_and_message.cpp")
    project.insert_suppression(altered_file)

    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_remote,
                                                'reports')
    codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                   '-e', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_remote)
    if ret:
        sys.exit(1)
    print('Analyzing new was successful.')

    # Store results again to the remote server. We need this second store to
    # set the detection status to the required states.
    ret = codechecker.store(codechecker_cfg, test_project_name_remote)
    if ret:
        sys.exit(1)
    print('Analyzing remote was successful.')

    # Save the run names in the configuration.
    codechecker_cfg['run_names'] = [test_project_name_remote]

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, test_config)


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
