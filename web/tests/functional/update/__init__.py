# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the package tests."""


import fnmatch
import os
import shutil
import sys
import uuid

from libtest import codechecker
from libtest import env
from libtest import plist_test
from libtest import project


TEST_WORKSPACE = None

test_dir = os.path.dirname(os.path.realpath(__file__))


def setup_package():
    """Setup the environment for the tests. """

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('update')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    test_project_name = uuid.uuid4().hex

    test_project_path = os.path.join(test_dir, "test_proj")

    temp_test_project_data = project.prepare(test_project_path, TEST_WORKSPACE)

    test_config['test_project'] = temp_test_project_data

    test_env = env.test_env(TEST_WORKSPACE)

    base_reports = os.path.join(temp_test_project_data['test_project_reports'],
                                'base')

    codechecker_cfg = {
        'suppress_file': None,
        'skip_list_file': None,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': [],
        'reportdir': base_reports
    }

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'update'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    ret = codechecker.store(codechecker_cfg,
                            test_project_name)
    if ret:
        sys.exit(1)
    print("Storing the base reports was succcessful.")

    codechecker_cfg['run_names'] = [test_project_name]

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
