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
    TEST_WORKSPACE = env.get_workspace('skip')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    test_config = {}

    project_info = project.get_info(test_project)

    test_config['test_project'] = project_info

    suppress_file = None

    # Generate skip list file for the tests.
    skip_list_file = os.path.join(TEST_WORKSPACE, 'skip_file')
    if os.path.isfile(skip_list_file):
        os.remove(skip_list_file)
    _generate_skip_list_file(skip_list_file)

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': []
    }

    ret = project.clean(test_project, test_env)
    if ret:
        sys.exit(ret)

    # Start or connect to the running CodeChecker server and get connection
    # details.
    print("This test uses a CodeChecker server... connecting...")
    server_access = codechecker.start_or_get_server()
    server_access['viewer_product'] = 'skip'
    codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

    # Extend the checker configuration with the server access.
    codechecker_cfg.update(server_access)

    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

    skip_file = codechecker_cfg.pop('skip_file')

    output_dir = codechecker_cfg['reportdir'] \
        if 'reportdir' in codechecker_cfg \
        else os.path.join(codechecker_cfg['workspace'], 'reports')

    codechecker_cfg['reportdir'] = output_dir

    # Analyze without skip.
    ret = codechecker.log_and_analyze(codechecker_cfg,
                                      project.path(test_project))
    if ret:
        print("Analyzing the test project without a skip file failed.")
        sys.exit(1)

    codechecker_cfg['skip_file'] = skip_file

    # Analyze with skip.
    ret = codechecker.log_and_analyze(codechecker_cfg,
                                      project.path(test_project))

    if ret:
        print("Analyzing the test project with a skip file failed.")
        sys.exit(1)

    ret = codechecker.store(codechecker_cfg,
                            test_project_name)
    if ret:
        print("Storing the results failed.")
        sys.exit(1)

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


def _generate_skip_list_file(skip_list_file):
    """
    Generate skip list file.
    file_to_be_skipped.cpp is a valid file in the cpp project
    with bugs in it.
    """
    skip_list_content = ["-*randtable.c", "-*blocksort.c", "-*huffman.c",
                         "-*decompress.c", "-*crctable.c",
                         "-*file_to_be_skipped.cpp", "-*path_end.h",
                         "-*skip.h"]
    print('Skip list file content: ' + skip_list_file)
    print('\n'.join(skip_list_content))

    s_file = open(skip_list_file, 'w', encoding="utf-8", errors="ignore")
    for k in skip_list_content:
        s_file.write(k + '\n')

    s_file.close()
