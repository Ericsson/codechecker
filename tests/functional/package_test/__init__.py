# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the package tests."""

import json
import multiprocessing
import os
import shlex
import shutil
import subprocess
import socket
import sys
import time
import uuid
from subprocess import CalledProcessError

# sys.path modification needed so nosetests can load the test_utils package.
sys.path.append(os.path.abspath(os.environ['TEST_TESTS_DIR']))

# Because of the nature of the python-env loading of nosetests, we need to
# add the codechecker_gen package to the pythonpath here, so it is available
# for the actual test cases.
__PKG_ROOT = os.path.abspath(os.environ['TEST_CODECHECKER_DIR'])
__LAYOUT_FILE_PATH = os.path.join(__PKG_ROOT, 'config', 'package_layout.json')
with open(__LAYOUT_FILE_PATH) as layout_file:
    __PACKAGE_LAYOUT = json.load(layout_file)
sys.path.append(os.path.join(
    __PKG_ROOT, __PACKAGE_LAYOUT['static']['codechecker_gen']))

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()

__shared = {}


def get_free_port():
    '''Get a free port from the OS.'''

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    free_port = s.getsockname()[1]
    s.close()

    return free_port


def _wait_for_postgres_shutdown(workspace):
    """
    Wait for PostgreSQL to shut down.
    Check if postmaster.pid file exists if yes postgres is still running.
    """
    max_wait_time = 60

    postmaster_pid_file = os.path.join(workspace,
                                       'pgsql_data',
                                       'postmaster.pid')

    while os.path.isfile(postmaster_pid_file):
        time.sleep(1)
        max_wait_time -= 1
        if max_wait_time == 0:
            break


def setup_package():
    """Setup the environment for the tests. Check the test project twice,
    then start the server."""
    pkg_root = os.path.abspath(os.environ['TEST_CODECHECKER_DIR'])

    env = os.environ.copy()
    env['PATH'] = os.path.join(pkg_root, 'bin') + ':' + env['PATH']

    tmp_dir = os.path.abspath(os.environ['TEST_CODECHECKER_PACKAGE_DIR'])
    workspace = os.path.join(tmp_dir, 'workspace')
    if os.path.exists(workspace):
        print("Removing previous workspace")
        shutil.rmtree(workspace)
    os.makedirs(workspace)

    test_project_path = os.path.join(
        os.path.abspath(os.environ['TEST_TESTS_DIR']),
        'test_projects',
        'test_files')

    clang_version = os.environ.get('TEST_CLANG_VERSION', 'stable')

    use_postgresql = os.environ.get('TEST_USE_POSTGRESQL', '') == 'true'

    pg_db_config = {}
    if use_postgresql:
        pg_db_config['dbaddress'] = 'localhost'
        pg_db_config['dbname'] = 'testDb'
        pg_db_config['dbport'] = os.environ.get('TEST_DBPORT', get_free_port())
        if os.environ.get('TEST_DBUSERNAME', False):
            pg_db_config['dbusername'] = os.environ['TEST_DBUSERNAME']

    project_info = \
        json.load(open(os.path.realpath(env['TEST_TEST_PROJECT_CONFIG'])))

    test_config = {
        'CC_TEST_SERVER_PORT': get_free_port(),
        'CC_TEST_SERVER_HOST': 'localhost',
        'CC_TEST_VIEWER_PORT': get_free_port(),
        'CC_TEST_VIEWER_HOST': 'localhost',
        'CC_AUTH_SERVER_PORT': get_free_port(),
        'CC_AUTH_SERVER_HOST': 'localhost',
        'CC_AUTH_VIEWER_PORT': get_free_port(),
        'CC_AUTH_VIEWER_HOST': 'localhost',
    }

    test_project_clean_cmd = project_info['clean_cmd']
    test_project_build_cmd = project_info['build_cmd']

    # setup env vars for test cases
    os.environ['CC_TEST_VIEWER_PORT'] = str(test_config['CC_TEST_VIEWER_PORT'])
    os.environ['CC_TEST_SERVER_PORT'] = str(test_config['CC_TEST_SERVER_PORT'])
    os.environ['CC_AUTH_SERVER_PORT'] = str(test_config['CC_AUTH_SERVER_PORT'])
    os.environ['CC_AUTH_VIEWER_PORT'] = str(test_config['CC_AUTH_VIEWER_PORT'])
    os.environ['CC_TEST_PROJECT_INFO'] = \
        json.dumps(project_info['clang_' + clang_version])
    # -------------------------------------------------------------------------

    # generate suppress file
    suppress_file = os.path.join(tmp_dir, 'suppress_file')
    if os.path.isfile(suppress_file):
        os.remove(suppress_file)
    _generate_suppress_file(suppress_file)

    skip_list_file = os.path.join(test_project_path, 'skip_list')

    shared_test_params = {
        'suppress_file': suppress_file,
        'env': env,
        'use_postgresql': use_postgresql,
        'workspace': workspace,
        'pg_db_config': pg_db_config
    }

    global __shared
    __shared = shared_test_params

    # First check.
    print("Running first analysis")

    ret = _clean_project(test_project_path,
                         test_project_clean_cmd,
                         env)
    if ret:
        sys.exit(ret)

    test_project_1_name = project_info['name'] + '_' + uuid.uuid4().hex

    ret = _run_check(shared_test_params,
                     skip_list_file,
                     test_project_build_cmd,
                     test_project_1_name,
                     test_project_path)
    _wait_for_postgres_shutdown(shared_test_params['workspace'])
    if ret:
        sys.exit(1)

    # Second check.
    print("Running second analysis")

    ret = _clean_project(test_project_path,
                         test_project_clean_cmd,
                         env)
    if ret:
        sys.exit(ret)

    test_project_2_name = project_info['name'] + '_' + uuid.uuid4().hex

    ret = _run_check(shared_test_params,
                     skip_list_file,
                     test_project_build_cmd,
                     test_project_2_name,
                     test_project_path)
    _wait_for_postgres_shutdown(shared_test_params['workspace'])
    if ret:
        sys.exit(1)

    update_check_name = 'update_test'
    # First check for update mode.
    print("Running first analysis for update test")

    ret = _clean_project(test_project_path,
                         test_project_clean_cmd,
                         env)
    if ret:
        sys.exit(ret)

    ret = _run_check(shared_test_params,
                     skip_list_file,
                     test_project_build_cmd,
                     update_check_name,
                     test_project_path)
    _wait_for_postgres_shutdown(shared_test_params['workspace'])
    if ret:
        sys.exit(1)

    # Second check for update mode.
    print("Running second analysis for update test")

    ret = _clean_project(test_project_path,
                         test_project_clean_cmd,
                         env)
    if ret:
        sys.exit(ret)

    checkers = ['-d', 'deadcode.DeadStores']
    ret = _run_check(shared_test_params,
                     skip_list_file,
                     test_project_build_cmd,
                     update_check_name,
                     test_project_path,
                     checkers)
    _wait_for_postgres_shutdown(shared_test_params['workspace'])
    if ret:
        sys.exit(1)

    # Start the CodeChecker server.
    print("Starting server to get results")
    _start_server(shared_test_params, test_config, False)

    #
    # Create a dummy authentication-enabled configuration and
    # an auth-enabled server.
    #
    # Running the tests only work if the initial value (in package
    # session_config.json) is FALSE for authentication.enabled.
    session_config_filename = "session_config.json"

    os.remove(os.path.join(shared_test_params['workspace'],
              session_config_filename))

    session_cfg_file = os.path.join(pkg_root,
                                    "config",
                                    session_config_filename)

    with open(session_cfg_file, 'r+') as scfg:
        __scfg_original = scfg.read()
        scfg.seek(0)
        try:
            scfg_dict = json.loads(__scfg_original)
        except ValueError as verr:
            print(verr)
            print('Malformed session config json.')
            sys.exit(1)

        scfg_dict["authentication"]["enabled"] = True
        scfg_dict["authentication"]["method_dictionary"]["enabled"] = True
        scfg_dict["authentication"]["method_dictionary"]["auths"] = ["cc:test"]

        json.dump(scfg_dict, scfg, indent=2, sort_keys=True)
        scfg.truncate()

    print("Starting server to test authentication")
    _start_server(shared_test_params, test_config, True)

    # Need to save the original configuration back so
    # multiple tests can work after each other.
    os.remove(os.path.join(shared_test_params['workspace'],
              session_config_filename))
    with open(session_cfg_file, 'w') as scfg:
        scfg.writelines(__scfg_original)


def teardown_package():
    """Stop the CodeChecker server."""
    __STOP_SERVER.set()

    time.sleep(10)


def _pg_db_config_to_cmdline_params(pg_db_config):
    """Format postgres config dict to CodeChecker cmdline parameters."""
    params = []

    for key, value in pg_db_config.items():
        params.append('--' + key)
        params.append(str(value))

    return params


def _clean_project(test_project_path, clean_cmd, env):
    """Clean the test project."""
    command = ['bash', '-c', clean_cmd]

    try:
        print(command)
        subprocess.check_call(command,
                              cwd=test_project_path,
                              env=env)
        return 0
    except subprocess.CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def _generate_suppress_file(suppress_file):
    """
    Create a dummy suppress file just to check if the old and the new
    suppress format can be processed.
    """
    print("Generating suppress file: " + suppress_file)

    import calendar
    import hashlib
    import random

    hash_version = '1'
    suppress_stuff = []
    for _ in range(10):
        curr_time = calendar.timegm(time.gmtime())
        random_integer = random.randint(1, 9999999)
        suppress_line = str(curr_time) + str(random_integer)
        suppress_stuff.append(
            hashlib.md5(suppress_line).hexdigest() + '#' + hash_version)

    s_file = open(suppress_file, 'w')
    for k in suppress_stuff:
        s_file.write(k + '||' + 'idziei éléáálk ~!@#$#%^&*() \n')
        s_file.write(
            k + '||' + 'test_~!@#$%^&*.cpp' +
            '||' + 'idziei éléáálk ~!@#$%^&*(\n')
        s_file.write(
            hashlib.md5(suppress_line).hexdigest() + '||' +
            'test_~!@#$%^&*.cpp' + '||' + 'idziei éléáálk ~!@#$%^&*(\n')

    s_file.close()


def _generate_skip_list_file(skip_list_file):
    """
    Create a dummy skip list file just to check if it can be loaded.
    Skip files without any results from checking.
    """
    skip_list_content = ["-*randtable.c", "-*blocksort.c", "-*huffman.c",
                         "-*decompress.c", "-*crctable.c"]

    s_file = open(skip_list_file, 'w')
    for k in skip_list_content:
        s_file.write(k + '\n')

    s_file.close()


def _run_check(shared_test_params, skip_list_file, test_project_build_cmd,
               test_project_name, test_project_path, checkers=[]):
    """
    Check a test project.

    :checkers parameter should be a list of enabled or disabled checkers
    Example: ['-d', 'deadcode.DeadStores']

    """
    check_cmd = ['CodeChecker', 'check',
                 '-w', shared_test_params['workspace'],
                 '--suppress', shared_test_params['suppress_file'],
                 '--skip', skip_list_file,
                 '-n', test_project_name,
                 '-b', "'" + test_project_build_cmd + "'",
                 '--analyzers', 'clangsa',
                 '--quiet-build']
    check_cmd.extend(checkers)

    if shared_test_params['use_postgresql']:
        check_cmd.append('--postgresql')
        check_cmd += _pg_db_config_to_cmdline_params(
            shared_test_params['pg_db_config'])

    try:
        print(' '.join(check_cmd))
        subprocess.check_call(
            shlex.split(' '.join(check_cmd)),
            cwd=test_project_path,
            env=shared_test_params['env'])

        print("Analyzing test project done.")
        return 0

    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


def _start_server_proc(event, server_cmd, checking_env):
    """Target function for starting the CodeChecker server."""
    proc = subprocess.Popen(server_cmd, env=checking_env)

    # Blocking termination until event is set.
    event.wait()

    # If proc is still running, stop it.
    if proc.poll() is None:
        proc.terminate()


def start_dummy_server(event, workspace, port):
    """Starts a dummy server that doesn't run checks on a different event
    so that the instance test can work."""

    server_cmd = ['CodeChecker', 'server',
                  '-w', workspace, '--view-port', str(port)]

    print(' '.join(server_cmd))
    server_proc = multiprocessing.Process(
        name='dummy-server',
        target=_start_server_proc,
        args=(event, server_cmd, __shared['env']))

    server_proc.start()

    time.sleep(5)


def _start_server(shared_test_params, test_config, auth=False):
    """Start the CodeChecker server."""

    server_cmd = ['CodeChecker', 'server',
                  '-w', shared_test_params['workspace'],
                  '--suppress', shared_test_params['suppress_file']]

    if auth:
        server_cmd.extend(['--check-port',
                           str(test_config['CC_AUTH_SERVER_PORT']),
                           '--view-port',
                           str(test_config['CC_AUTH_VIEWER_PORT'])])
    else:
        server_cmd.extend(['--check-port',
                           str(test_config['CC_TEST_SERVER_PORT']),
                           '--view-port',
                           str(test_config['CC_TEST_VIEWER_PORT'])])
    if shared_test_params['use_postgresql']:
        server_cmd.append('--postgresql')
        server_cmd += _pg_db_config_to_cmdline_params(
            shared_test_params['pg_db_config'])

    print(' '.join(server_cmd))
    server_proc = multiprocessing.Process(
        name=('server' if not auth else 'auth-server'),
        target=_start_server_proc,
        args=(__STOP_SERVER, server_cmd, shared_test_params['env']))

    server_proc.start()

    # Wait for server to start and connect to database.
    time.sleep(10)
