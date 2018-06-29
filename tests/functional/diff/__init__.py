# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the package tests."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from distutils import dir_util
import os
import shutil
import sys
import uuid

from libtest import codechecker
from libtest import env
from libtest import project

# Test workspace used to diff tests.
TEST_WORKSPACE = None


def insert_suppression(source_file_name):
    with open(source_file_name, 'r') as f:
        content = f.read()
    content = content.replace("insert_suppress_here",
                              "codechecker_suppress [all] test suppression!")
    with open(source_file_name, 'w') as f:
        f.write(content)


def setup_package():
    """
    Setup the environment for the tests.
    Check the test project twice.
    """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('diff')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_project_path = project.path(test_project)
    test_project_path_altered = os.path.join(TEST_WORKSPACE, "cpp_copy")
    # We create a copy of the test project which we will change
    # to simulate code editing.
    dir_util.copy_tree(test_project_path, test_project_path_altered)

    test_config = {}

    project_info = project.get_info(test_project)

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'force': True,
        'workspace': TEST_WORKSPACE,
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
        'checkers': ['-d', 'core.CallAndMessage',
                     '-e', 'core.StackAddressEscape']
    }

    test_config['codechecker_cfg'] = codechecker_cfg

    ret = project.clean(test_project, test_env)
    if ret:
        sys.exit(ret)

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'diff'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    test_project_name_base = project_info['name'] + '_' + uuid.uuid4().hex

    ret = codechecker.check(codechecker_cfg,
                            test_project_name_base,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("First analysis of the test project was successful.")

    ret = project.clean(test_project, test_env)
    if ret:
        sys.exit(ret)

    test_project_name_new = project_info['name'] + '_' + uuid.uuid4().hex

    # Let's run the second analysis with different
    # checkers to have some real difference.
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.StackAddressEscape'
                                   ]
    ret = codechecker.check(codechecker_cfg,
                            test_project_name_new,
                            test_project_path_altered)
    if ret:
        sys.exit(1)
    print("Second analysis of the test project was successful.")

    # Insert a real suppression into the code

    altered_file = os.path.join(test_project_path_altered,
                                "call_and_message.cpp")
    insert_suppression(altered_file)

    # Run the second analysis results
    # into a report directory
    ret = codechecker.analyze(codechecker_cfg,
                              test_project_name_new,
                              test_project_path_altered)
    if ret:
        sys.exit(1)
    print("CodeChecker analyze of test project was successful.")

    test_project_name_update = project_info['name'] + '_' + uuid.uuid4().hex
    codechecker_cfg['tag'] = 't1'
    codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                   '-e', 'core.StackAddressEscape'
                                   ]
    codechecker_cfg['reportdir'] = os.path.join(TEST_WORKSPACE, 'reports2')

    ret = codechecker.check(codechecker_cfg,
                            test_project_name_update,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("Third analysis of the test project was successful.")

    codechecker_cfg['tag'] = 't2'
    codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                   '-d', 'core.StackAddressEscape'
                                   ]
    ret = codechecker.check(codechecker_cfg,
                            test_project_name_update,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("Fourth analysis of the test project was successful.")

    codechecker_cfg['tag'] = 't3'
    ret = codechecker.check(codechecker_cfg,
                            test_project_name_update,
                            test_project_path)
    if ret:
        sys.exit(1)
    print("Fifth analysis of the test project was successful.")

    # Order of the test run names matter at comparison!
    codechecker_cfg['run_names'] = [test_project_name_base,
                                    test_project_name_new,
                                    test_project_name_update]

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export test configuration to the workspace.
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
    shutil.rmtree(TEST_WORKSPACE)
