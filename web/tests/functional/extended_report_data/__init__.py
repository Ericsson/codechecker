# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the test package extended_report_data."""


import os
import shutil
import sys

from libtest import codechecker
from libtest import env
from libtest import project

# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing detection_status."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('extended_report_data')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_env = env.test_env(TEST_WORKSPACE)

    # Configuration options.
    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'run_names': []
    }

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'extended_report_data'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    # Copy test projects and replace file path in plist files.
    test_projects = ['notes', 'macros']
    for test_project in test_projects:
        test_project_path = os.path.join(TEST_WORKSPACE, "test_proj",
                                         test_project)
        shutil.copytree(project.path(test_project), test_project_path)

        for test_file in os.listdir(test_project_path):
            if test_file.endswith(".plist"):
                test_file_path = os.path.join(test_project_path, test_file)
                with open(test_file_path, 'r+',
                          encoding="utf-8", errors="ignore") as plist_file:
                    content = plist_file.read()
                    new_content = content.replace("$FILE_PATH$",
                                                  test_project_path)
                    plist_file.seek(0)
                    plist_file.truncate()
                    plist_file.write(new_content)

        codechecker_cfg['reportdir'] = test_project_path

        ret = codechecker.store(codechecker_cfg, test_project)
        if ret:
            sys.exit(1)
        print("Analyzing test project was succcessful.")

        codechecker_cfg['run_names'].append(test_project)

    # Export the test configuration to the workspace.
    env.export_test_cfg(TEST_WORKSPACE, {'codechecker_cfg': codechecker_cfg})


def teardown_package():
    """Clean up after the test."""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing: " + TEST_WORKSPACE)
    # shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
