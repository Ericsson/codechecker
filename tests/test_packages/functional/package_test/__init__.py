# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""DOC."""

import json
import multiprocessing
import os
import subprocess
import sys
import time
import uuid

sys.path.append(os.path.abspath(os.environ['TEST_TESTS_DIR']))
from test_utils import get_free_port

__PKG_ROOT = os.path.abspath(os.environ['TEST_CODECHECKER_DIR'])
__LAYOUT_FILE_PATH = os.path.join(__PKG_ROOT, 'config', 'package_layout.json')
with open(__LAYOUT_FILE_PATH) as layout_file:
    __PACKAGE_LAYOUT = json.load(layout_file)
sys.path.append(os.path.join(
    __PKG_ROOT, __PACKAGE_LAYOUT['static']['codechecker_gen']))

# stopping event for CodeChecker server
__STOP_SERVER = multiprocessing.Event()


def setup_package():
    """DOC."""
    # Set internal env
    pkg_root = os.path.abspath(os.environ['TEST_CODECHECKER_DIR'])
    env = os.environ.copy()
    env['PATH'] = os.path.join(pkg_root, 'bin') + ':' + env['PATH']

    tmp_dir = os.path.abspath(os.environ['TEST_CODECHECKER_PACKAGE_DIR'])
    workspace = os.path.join(tmp_dir, 'workspace')
    if not os.path.exists(workspace):
        os.makedirs(workspace)

    test_project_path = os.path.join(
        os.path.abspath(os.environ['TEST_TESTS_DIR']),
        'test_projects',
        'test_files')

    clang_version = os.environ['TEST_CLANG_VERSION']

    database = {
        'dbaddress': 'localhost',
        'dbport': os.environ['TEST_DBPORT'],
        'dbname': 'testDb',
        'dbusername': os.environ['TEST_DBUSERNAME']
    }

    project_info = \
        json.load(open(os.path.join(test_project_path, 'project_info.json')))

    use_postgresql = os.environ.get('TEST_USE_POSTGRESQL') == 'true'

    test_config = {}
    test_config['CC_TEST_SERVER_PORT'] = get_free_port()
    test_config['CC_TEST_SERVER_HOST'] = 'localhost'
    test_config['CC_TEST_VIEWER_PORT'] = get_free_port()
    test_config['CC_TEST_VIEWER_HOST'] = 'localhost'

    test_project_clean_cmd = project_info['clean_cmd']
    test_project_build_cmd = project_info['build_cmd']

    # setup env vars for test cases
    os.environ['CC_TEST_VIEWER_PORT'] = str(test_config['CC_TEST_VIEWER_PORT'])
    os.environ['CC_TEST_SERVER_PORT'] = str(test_config['CC_TEST_SERVER_PORT'])
    os.environ['CC_TEST_PROJECT_INFO'] = \
        json.dumps(project_info['clang_' + clang_version])
    # -------------------------------------------------------------------------

    # generate suppress file
    suppress_file = os.path.join(tmp_dir, 'suppress_file')
    if os.path.isfile(suppress_file):
        os.remove(suppress_file)
    _generate_suppress_file(suppress_file)

    # generate skip list file
    skip_list_file = os.path.join(tmp_dir, 'skip_list_file')
    if os.path.isfile(skip_list_file):
        os.remove(skip_list_file)
    _generate_skip_list_file(skip_list_file)

    # first check
    _clean_project(test_project_path, test_project_clean_cmd, env)
    test_project_1_name = project_info['name'] + '_' + uuid.uuid4().hex

    _run_check(
        suppress_file, skip_list_file, database, use_postgresql,
        test_project_build_cmd, workspace, test_project_1_name,
        test_project_path, env)

    time.sleep(5)

    # second check
    _clean_project(test_project_path, test_project_clean_cmd, env)

    test_project_2_name = project_info['name'] + '_' + uuid.uuid4().hex

    _run_check(
        suppress_file, skip_list_file, database, use_postgresql,
        test_project_build_cmd, workspace, test_project_2_name,
        test_project_path, env)

    time.sleep(5)

    # start the CodeChecker server
    _start_server(database, test_config, workspace, suppress_file, env,
                  use_postgresql)


def teardown_package():
    """DOC."""
    __STOP_SERVER.set()

    time.sleep(10)


def _clean_project(test_project_path, clean_cmd, env):
    """DOC."""
    command = ['bash', '-c', clean_cmd]

    try:
        subprocess.check_call(command, cwd=test_project_path, env=env)
    except subprocess.CalledProcessError as perr:
        raise perr


def _generate_suppress_file(suppress_file):
    """
    Create a dummy supppress file just to check if the old and the new
    suppress format can be processed.
    """
    import calendar
    import hashlib
    import random

    hash_version = '1'
    suppress_stuff = []
    for _ in range(10):
        t = calendar.timegm(time.gmtime())
        r = random.randint(1, 9999999)
        n = str(t) + str(r)
        suppress_stuff.append(hashlib.md5(n).hexdigest() + '#' + hash_version)

    s_file = open(suppress_file, 'w')
    for k in suppress_stuff:
        s_file.write(k + '||' + 'idziei éléáálk ~!@#$#%^&*() \n')
        s_file.write(
            k + '||' + 'test_~!@#$%^&*.cpp' +
            '||' 'idziei éléáálk ~!@#$%^&*(\n')
        s_file.write(
            hashlib.md5(n).hexdigest() + '||' + 'test_~!@#$%^&*.cpp' +
            '||' 'idziei éléáálk ~!@#$%^&*(\n')

    s_file.close()


def _generate_skip_list_file(skip_list_file):
    """
    Create a dummy skip list file just to check if it can be loaded.
    Skip files without any results from checking.
    """
    skip_list_content = []
    skip_list_content.append("-*randtable.c")
    skip_list_content.append("-*blocksort.c")
    skip_list_content.append("-*huffman.c")
    skip_list_content.append("-*decompress.c")
    skip_list_content.append("-*crctable.c")

    s_file = open(skip_list_file, 'w')
    for k in skip_list_content:
        s_file.write(k + '\n')

    s_file.close()


def _run_check(suppress_file, skip_list_file, database, use_postgresql,
               test_project_build_cmd, workspace, test_project_name,
               test_project_path, env):
    """DOC."""
    check_cmd = []
    check_cmd.append('CodeChecker')
    check_cmd.append('check')
    check_cmd.append('-w')
    check_cmd.append(workspace)
    check_cmd.append('--suppress')
    check_cmd.append(suppress_file)
    check_cmd.append('--skip')
    check_cmd.append(skip_list_file)
    check_cmd.append('-n')
    check_cmd.append(test_project_name)
    check_cmd.append('-b')
    check_cmd.append(test_project_build_cmd)
    check_cmd.append('--analyzers')
    check_cmd.append('clangsa')
    if use_postgresql:
        check_cmd.append('--postgresql')
        check_cmd.append('--dbaddress')
        check_cmd.append(database['dbaddress'])
        check_cmd.append('--dbport')
        check_cmd.append(str(database['dbport']))
        check_cmd.append('--dbname')
        check_cmd.append(database['dbname'])
        check_cmd.append('--dbusername')
        check_cmd.append(database['dbusername'])

    try:
        subprocess.check_call(check_cmd, cwd=test_project_path, env=env)
    except subprocess.CalledProcessError as perr:
        raise perr


def _start_server(database, test_config, workspace, suppress_file, env,
                  use_postgresql):
    """DOC."""
    def start_server_proc(event, server_cmd, checking_env):
        """DOC."""
        proc = subprocess.Popen(server_cmd, env=checking_env)

        # Blocking termination until event is set.
        event.wait()

        # If proc is still running, stop it.
        if proc.poll() is None:
            proc.terminate()
    # -------------------------------------------------------------------------

    server_cmd = []
    server_cmd.append('CodeChecker')
    server_cmd.append('server')
    server_cmd.append('--check-port')
    server_cmd.append(str(test_config['CC_TEST_SERVER_PORT']))
    server_cmd.append('--view-port')
    server_cmd.append(str(test_config['CC_TEST_VIEWER_PORT']))
    server_cmd.append('-w')
    server_cmd.append(workspace)
    server_cmd.append('--suppress')
    server_cmd.append(suppress_file)
    if use_postgresql:
        server_cmd.append('--postgresql')
        server_cmd.append('--dbaddress')
        server_cmd.append(database['dbaddress'])
        server_cmd.append('--dbport')
        server_cmd.append(str(database['dbport']))
        server_cmd.append('--dbname')
        server_cmd.append(database['dbname'])
        server_cmd.append('--dbusername')
        server_cmd.append(database['dbusername'])

    server_proc = multiprocessing.Process(
        name='server',
        target=start_server_proc,
        args=(__STOP_SERVER, server_cmd, env))

    server_proc.start()

    # wait for server to start and connect to database
    time.sleep(10)
