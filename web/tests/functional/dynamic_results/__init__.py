# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Setup for the test package dynamic_results."""


import os
import shutil
import sys

from libtest import codechecker
from libtest import env
from libtest import project


# Test workspace should be initialized in this module.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for testing dynamic_results."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('dynamic_results')

    # Set the TEST_WORKSPACE used by the tests.
    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    shutil.copytree(
        project.path("dynamic"), TEST_WORKSPACE, dirs_exist_ok=True)

    for plist in os.listdir(TEST_WORKSPACE):
        if plist.endswith('.plist'):
            with open(os.path.join(TEST_WORKSPACE, plist), 'r+',
                      encoding='utf-8',
                      errors='ignore') as plist_file:
                content = plist_file.read()
                new_content = content.replace("$FILE_PATH$", TEST_WORKSPACE)
                plist_file.seek(0)
                plist_file.truncate()
                plist_file.write(new_content)

    server_access = codechecker.start_or_get_server()
    server_access["viewer_product"] = "dynamic_results"
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    codechecker_cfg = {
        'workspace': TEST_WORKSPACE,
        'reportdir': TEST_WORKSPACE,
        'check_env': env.test_env(TEST_WORKSPACE)
    }

    codechecker_cfg.update(server_access)

    env.export_test_cfg(TEST_WORKSPACE, {
        'codechecker_cfg': codechecker_cfg
    })

    if codechecker.store(codechecker_cfg, "dynamic_results"):
        sys.exit(1)


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
