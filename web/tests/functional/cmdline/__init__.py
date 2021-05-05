# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the package tests."""


import os
import shutil
import sys
import uuid

from libtest import codechecker
from libtest import env
from libtest import project


TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('cmdline')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_config = {}

    project_info = project.get_info(test_project)

    # Copy the test project to the workspace. The tests should
    # work only on this test project.
    test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
    shutil.copytree(project.path(test_project), test_proj_path)

    project_info['project_path'] = test_proj_path

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'description': "Runs for command line test."
    }

    ret = project.clean(test_project)
    if ret:
        sys.exit(ret)

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'cmdline'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Generate a unique name for this test run.
    test_project_name_1 = project_info['name'] + '1_' + uuid.uuid4().hex

    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_1,
                                      project.path(test_project))
    if ret:
        sys.exit(1)
    print("Analyzing the test project was successful.")

    test_project_name_2 = project_info['name'] + '2_' + uuid.uuid4().hex

    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_2,
                                      project.path(test_project))
    if ret:
        sys.exit(1)
    print("Analyzing the test project was successful.")

    codechecker_cfg['run_names'] = [test_project_name_1, test_project_name_2]

    test_config['codechecker_cfg'] = codechecker_cfg

    env.export_test_cfg(TEST_WORKSPACE, test_config)


def teardown_package():
    """Clean up after the test."""

    # TODO: if environment variable is set keep the workspace
    # and print out the path
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
