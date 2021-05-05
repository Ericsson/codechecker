# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Setup for the test package component."""


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
    """Setup the environment for testing components."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('component')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_config = {}

    project_info = project.get_info(test_project)

    test_project_path = os.path.join(TEST_WORKSPACE, "test_proj")
    shutil.copytree(project.path(test_project), test_project_path)

    project_info['project_path'] = test_project_path

    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

    test_config['test_project'] = project_info

    suppress_file = None

    skip_list_file = None

    test_env = env.test_env(TEST_WORKSPACE)

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
    server_access = codechecker.start_or_get_server(auth_required=True)
    server_access['viewer_product'] = 'component'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Clean the test project, if needed by the tests.
    ret = project.clean(test_project_path)
    if ret:
        sys.exit(ret)

    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name,
                                      test_project_path)
    if ret:
        sys.exit(1)
    print("Analyzing test project was succcessful.")

    # Save the run names in the configuration.
    codechecker_cfg['run_names'] = [test_project_name]

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
