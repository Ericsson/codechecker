# coding=utf-8
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import os
from libtest import env
from libtest import codechecker

TEST_WORKSPACE = None


def setup_class():
    """Setup the test environment with a CodeChecker server."""
    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace("filter_preset")

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_env = env.test_env(TEST_WORKSPACE)

    print("Starting CodeChecker server for filter preset API tests...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'filter_preset_test'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE
    }
    codechecker_cfg.update(server_access)

    test_config = {'codechecker_cfg': codechecker_cfg}
    env.export_test_cfg(TEST_WORKSPACE, test_config)


def teardown_class():
    """Clean up after the test."""
    global TEST_WORKSPACE

    check_env = env.import_test_cfg(TEST_WORKSPACE)[
        'codechecker_cfg']['check_env']
    codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

    print("Removing test workspace: " + TEST_WORKSPACE)
    import shutil
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
