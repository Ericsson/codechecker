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


def setup_class_common(workspace_name):
    """
    Setup the environment for the tests.

    This test suite analyzes and stores a sample project with different
    configurations in different runs and tags. The test cases are observing the
    effect of configurations by checking the number of results. The number of
    reports by checkers are commented above the specific configurations so it
    is easier to see the content of the current analysis.

    There is no concept behind which checkers are enabled or disabled during an
    analysis. The point is that the result sets are different in the runs.
    """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace(workspace_name)

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

    # -----------------------------------------------------
    # Checker name                      | Number of reports
    # -----------------------------------------------------
    # clang-diagnostic-division-by-zero |                 3
    # clang-diagnostic-return-type      |                 5
    # core.CallAndMessage               |                 5
    # core.DivideZero                   |                10
    # core.NullDereference              |                 4
    # core.StackAddressEscape           |                 3
    # cplusplus.NewDelete               |                 5
    # deadcode.DeadStores               |                 6
    # misc-definitions-in-headers       |                 2
    # unix.Malloc                       |                 1
    # -----------------------------------------------------

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': ['-d', 'clang-diagnostic',
                     '-e', 'clang-diagnostic-division-by-zero',
                     '-e', 'clang-diagnostic-return-type'],
        'tag': tag,
        'analyzers': ['clangsa', 'clang-tidy']
    }

    ret = project.clean(test_project)
    if ret:
        sys.exit(ret)

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = workspace_name
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

    # -----------------------------------------------------
    # Checker name                      | Number of reports
    # -----------------------------------------------------
    # clang-diagnostic-division-by-zero |                 3
    # core.CallAndMessage               |                 5
    # core.DivideZero                   |                10
    # core.NullDereference              |                 4
    # cplusplus.NewDelete               |                 5
    # deadcode.DeadStores               |                 6
    # misc-definitions-in-headers       |                 2
    # -----------------------------------------------------

    # Let's run the second analysis with different
    # checkers to have some real difference.
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.StackAddressEscape',
                                   '-d', 'unix.Malloc',
                                   '-d', 'clang-diagnostic',
                                   '-e', 'clang-diagnostic-division-by-zero'
                                   ]
    codechecker_cfg['tag'] = None
    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_new,
                                      project.path(test_project))

    if ret:
        sys.exit(1)
    print("Second analysis of the test project was successful.")

    test_project_name_third = project_info['name'] + uuid.uuid4().hex

    # -----------------------------------------------------
    # Checker name                      | Number of reports
    # -----------------------------------------------------
    # clang-diagnostic-division-by-zero |                 3
    # core.CallAndMessage               |                 5
    # core.DivideZero                   |                10
    # core.NullDereference              |                 4
    # cplusplus.NewDelete               |                 5
    # deadcode.DeadStores               |                 6
    # misc-definitions-in-headers       |                 2
    # unix.Malloc                       |                 1
    # -----------------------------------------------------

    # Let's run the third analysis.
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.StackAddressEscape',
                                   '-d', 'clang-diagnostic',
                                   '-e', 'clang-diagnostic-division-by-zero'
                                   ]
    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name_third,
                                      project.path(test_project))

    if ret:
        sys.exit(1)
    print("Third analysis of the test project was successful.")

    # -----------------------------------------------------
    # Checker name                      | Number of reports
    # -----------------------------------------------------
    # clang-diagnostic-division-by-zero |                 3
    # clang-diagnostic-return-type      |                 5
    # core.CallAndMessage               |                 5
    # core.DivideZero                   |                10
    # core.NullDereference              |                 4
    # cplusplus.NewDelete               |                 5
    # deadcode.DeadStores               |                 6
    # misc-definitions-in-headers       |                 2
    # -----------------------------------------------------

    # Let's run the second analysis and updat the same run.
    codechecker_cfg['checkers'] = ['-d', 'core.StackAddressEscape',
                                   '-d', 'unix.Malloc',
                                   '-d', 'clang-diagnostic',
                                   '-e', 'clang-diagnostic-division-by-zero',
                                   '-e', 'clang-diagnostic-return-type']
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


def teardown_class_common():
    """Clean up after the test."""

    # TODO: if environment variable is set keep the workspace
    # and print out the path
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
