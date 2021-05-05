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
    TEST_WORKSPACE = env.get_workspace('report_viewer_api')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_config = {}

    project_info = project.get_info(test_project)

    test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
    shutil.copytree(project.path(test_project), test_proj_path)

    project_info['project_path'] = test_proj_path

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    tag = 'v1.0'

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': ['-e', 'clang-diagnostic-return-type'],
        'tag': tag
    }

    ret = project.clean(test_project)
    if ret:
        sys.exit(ret)

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'report_viewer_api'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex + '**'

    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name,
                                      project.path(test_project))
    if ret:
        sys.exit(1)
    print("Analyzing the test project was successful.")

    test_project_name_new = project_info['name'] + '*' + uuid.uuid4().hex + '%'

    # Let's run the second analysis with different
    # checkers to have some real difference.
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.StackAddressEscape',
                                   '-d', 'unix.Malloc'
                                   ]
    codechecker_cfg['tag'] = None
    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_new,
                                      project.path(test_project))

    if ret:
        sys.exit(1)
    print("Second analysis of the test project was successful.")

    test_project_name_third = project_info['name'] + uuid.uuid4().hex

    # Let's run the third analysis.
    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_third,
                                      project.path(test_project))

    if ret:
        sys.exit(1)
    print("Third analysis of the test project was successful.")

    # Let's run the second analysis and updat the same run.
    codechecker_cfg['checkers'] = ['-d', 'core.StackAddressEscape']
    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_third,
                                      project.path(test_project))

    if ret:
        sys.exit(1)
    print("4th analysis of the test project was successful.")

    codechecker_cfg['run_names'] = [test_project_name,
                                    test_project_name_new]

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
