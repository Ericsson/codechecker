# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Setup for the test package cleanup plan."""


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
    """Setup the environment for the tests. """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('cleanup_plan')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_project_path = project.path(test_project)

    test_config = {}

    project_info = project.get_info(test_project)

    test_config['test_project'] = project_info
    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
        'checkers': []
    }

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'cleanup_plan'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Check the test project for the first time.
    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex
    ret = codechecker.check_and_store(codechecker_cfg,
                                      test_project_name,
                                      test_project_path)
    if ret:
        sys.exit(1)
    print("Analyzing test project was successful.")

    codechecker_cfg['run_names'] = [test_project_name]
    test_config['codechecker_cfg'] = codechecker_cfg
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
