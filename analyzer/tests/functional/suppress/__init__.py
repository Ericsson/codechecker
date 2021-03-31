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

from libtest import codechecker
from libtest import env
from libtest import project

TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('suppress')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'suppress'

    test_config = {}

    project_info = project.get_info(test_project)

    test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
    shutil.copytree(project.path(test_project), test_proj_path)

    project_info['project_path'] = test_proj_path

    test_config['test_project'] = project_info

    # Generate a suppress file for the tests.
    suppress_file = os.path.join(TEST_WORKSPACE, 'suppress_file')
    if os.path.isfile(suppress_file):
        os.remove(suppress_file)
    _generate_suppress_file(suppress_file)

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'suppress_file': None,
        'skip_list_file': None,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': []
    }

    ret = project.clean(test_project, test_env)
    if ret:
        sys.exit(ret)

    output_dir = codechecker_cfg['reportdir'] \
        if 'reportdir' in codechecker_cfg \
        else os.path.join(codechecker_cfg['workspace'], 'reports')

    codechecker_cfg['reportdir'] = output_dir

    ret = codechecker.log_and_analyze(codechecker_cfg,
                                      project.path(test_project))

    if ret:
        sys.exit(1)
    print("Analyzing the test project was successful.")

    test_config['codechecker_cfg'] = codechecker_cfg

    env.export_test_cfg(TEST_WORKSPACE, test_config)


def teardown_package():
    """Clean up after the test."""

    # TODO: If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)


def _generate_suppress_file(suppress_file):
    """
    Create a dummy suppress file just to check if the old and the new
    suppress format can be processed.
    """
    print("Generating suppress file: " + suppress_file)

    import calendar
    import hashlib
    import random
    import time

    hash_version = '1'
    suppress_stuff = []
    for _ in range(10):
        curr_time = calendar.timegm(time.gmtime())
        random_integer = random.randint(1, 9999999)
        suppress_line = str(curr_time) + str(random_integer)
        suppress_stuff.append(
            hashlib.md5(suppress_line.encode("utf-8")).hexdigest() +
            '#' + hash_version)

    s_file = open(suppress_file, 'w', encoding='utf-8', errors='ignore')
    for k in suppress_stuff:
        s_file.write(k + '||' + 'idziei éléáálk ~!@#$#%^&*() \n')
        s_file.write(
            k + '||' + 'test_~!@#$%^&*.cpp' +
            '||' + 'idziei éléáálk ~!@#$%^&*(\n')
        s_file.write(
            hashlib.md5(suppress_line.encode("utf-8")).hexdigest() + '||' +
            'test_~!@#$%^&*.cpp' + '||' + 'idziei éléáálk ~!@#$%^&*(\n')

    s_file.close()
