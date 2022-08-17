# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the test package diff_local_remote_suppress."""


import os
import shutil
import sys
import uuid

from libtest import codechecker
from libtest import env
from libtest import project


def init_projects():
    """
    Setup the environment for testing diff_local_remote_suppress.

    Original project
    ------------------------------------------------------
    Checker name            | Severity | Number of reports
    ------------------------------------------------------
    core.CallAndMessage     | HIGH     |                 5
    core.DivideZero         | HIGH     |                10
    core.NullDereference    | HIGH     |                 4
    core.StackAddressEscape | HIGH     |                 3
    cplusplus.NewDelete     | HIGH     |                 5
    deadcode.DeadStores     | LOW      |                 6
    unix.Malloc             | MEDIUM   |                 1
    ------------------------------------------------------

    Project 1
    ------------------------------------------------------
    Checker name            | Severity | Number of reports
    ------------------------------------------------------
    core.CallAndMessage     | HIGH     |                 4 (1 suppressed)
    core.DivideZero         | HIGH     |                10
    core.StackAddressEscape | HIGH     |                 3
    cplusplus.NewDelete     | HIGH     |                 5
    deadcode.DeadStores     | LOW      |                 6
    unix.Malloc             | MEDIUM   |                 1
    ------------------------------------------------------

    Project 2
    ------------------------------------------------------
    Checker name            | Severity | Number of reports
    ------------------------------------------------------
    core.DivideZero         | HIGH     |                 9 (1 suppressed)
    core.NullDereference    | HIGH     |                 4
    core.StackAddressEscape | HIGH     |                 3
    cplusplus.NewDelete     | HIGH     |                 5
    deadcode.DeadStores     | LOW      |                 5 (1 suppressed)
    unix.Malloc             | MEDIUM   |                 1
    ------------------------------------------------------
    """

    TEST_WORKSPACE = os.environ['TEST_WORKSPACE']

    test_project = 'cpp'

    project_info = project.get_info(test_project)

    # Config options.

    codechecker_cfg = {
        'suppress_file': None,
        'skip_list_file': None,
        'check_env': env.test_env(TEST_WORKSPACE),
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'analyzers': ['clangsa'],
        'run_names': {}
    }

    test_config = {}
    test_config['test_project'] = project_info
    test_config['codechecker_cfg'] = codechecker_cfg

    # Start or connect to the running CodeChecker server and get connection
    # details.

    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'diff_local_remote_suppress'
    codechecker_cfg.update(server_access)

    env.export_test_cfg(TEST_WORKSPACE, test_config)
    cc_client = env.setup_viewer_client(TEST_WORKSPACE)
    for run_data in cc_client.getRunData(None, None, 0, None):
        cc_client.removeRun(run_data.runId, None)

    # Copy "cpp" test project 3 times to different directories.

    test_proj_path_orig = os.path.join(TEST_WORKSPACE, "test_proj_orig")
    test_proj_path_1 = os.path.join(TEST_WORKSPACE, "test_proj_1")
    test_proj_path_2 = os.path.join(TEST_WORKSPACE, "test_proj_2")

    shutil.rmtree(test_proj_path_orig, ignore_errors=True)
    shutil.rmtree(test_proj_path_1, ignore_errors=True)
    shutil.rmtree(test_proj_path_2, ignore_errors=True)
    shutil.copytree(project.path(test_project), test_proj_path_orig)
    shutil.copytree(project.path(test_project), test_proj_path_1)
    shutil.copytree(project.path(test_project), test_proj_path_2)

    project_info['project_path_orig'] = test_proj_path_orig
    project_info['project_path_1'] = test_proj_path_1
    project_info['project_path_2'] = test_proj_path_2

    # Log, analyze and store original project.
    # No changes in the project.

    codechecker_cfg['workspace'] = test_proj_path_orig
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_orig, 'reports')

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_orig)
    if ret:
        sys.exit(1)

    run_name_project_orig = project_info['name'] + '_' + uuid.uuid4().hex
    codechecker_cfg['run_names']['test_project_orig'] = run_name_project_orig
    ret = codechecker.store(codechecker_cfg, run_name_project_orig)
    if ret:
        sys.exit(1)

    # Log, analyze and store project 1.
    # Modifications:
    #   - Suppress a core.CallAndMessage report.
    #   - Options: "-e core.CallAndMessage -d core.NullDereference"

    project.insert_suppression(
        os.path.join(test_proj_path_1, "call_and_message.cpp"))

    codechecker_cfg['workspace'] = test_proj_path_1
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_1, 'reports')
    codechecker_cfg['checkers'] = [
        '-e', 'core.CallAndMessage', '-d', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_1)
    if ret:
        sys.exit(1)

    run_name_project_1 = project_info['name'] + '_' + uuid.uuid4().hex
    codechecker_cfg['run_names']['test_project_1'] = run_name_project_1
    ret = codechecker.store(codechecker_cfg, run_name_project_1)
    if ret:
        sys.exit(1)

    # Log, analyze and store project 2.
    # Modifications:
    #   - Suppress a core.DivideZero report.
    #   - Options: "-d core.CallAndMessage -e core.NullDereference"

    project.insert_suppression(
        os.path.join(test_proj_path_2, "divide_zero.cpp"))

    codechecker_cfg['workspace'] = test_proj_path_2
    codechecker_cfg['reportdir'] = os.path.join(test_proj_path_2, 'reports')
    codechecker_cfg['checkers'] = [
        '-d', 'core.CallAndMessage', '-e', 'core.NullDereference']

    ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_2)
    if ret:
        sys.exit(1)

    run_name_project_2 = project_info['name'] + '_' + uuid.uuid4().hex
    codechecker_cfg['run_names']['test_project_2'] = run_name_project_2
    ret = codechecker.store(codechecker_cfg, run_name_project_2)
    if ret:
        sys.exit(1)

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, test_config)


def setup_package():
    """
    The test files in this diff_local_remote_suppress test share the analyzed
    projects. These tests are checking report suppression where the order of
    suppressions matters. Since we can't rely on the ordering of tests, the
    projects are set up by these tests individually. The setup happens in
    function init_projects() and that is imported and executed in each test.
    """
    os.environ['TEST_WORKSPACE'] = \
        env.get_workspace('diff_local_remote_suppress')

    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'diff_local_remote_suppress'
    codechecker.add_test_package_product(
        server_access, os.environ['TEST_WORKSPACE'])


def teardown_package():
    TEST_WORKSPACE = os.environ['TEST_WORKSPACE']

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
