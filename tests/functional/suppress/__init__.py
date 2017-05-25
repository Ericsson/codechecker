# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the package tests."""

import multiprocessing
import os
import shutil
import subprocess
import sys
import time
import uuid

from libtest import project
from libtest import codechecker
from libtest import env

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocessing.Event()
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests. Check the test project twice,
    then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('suppress')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_project = 'cpp'

    pg_db_config = env.get_postgresql_cfg()

    test_config = {}

    project_info = project.get_info(test_project)

    test_config['test_project'] = project_info

    # Generate a suppress file for the tests.
    suppress_file = os.path.join(TEST_WORKSPACE, 'suppress_file')
    if os.path.isfile(suppress_file):
        os.remove(suppress_file)
    _generate_suppress_file(suppress_file)

    skip_list_file = None

    # Get port numbers for the tests.
    host_port_cfg = env.get_host_port_cfg()

    test_env = env.test_env()

    codechecker_cfg = {
        'suppress_file': suppress_file,
        'skip_list_file': skip_list_file,
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'pg_db_config': pg_db_config,
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)

    ret = project.clean(test_project, test_env)
    if ret:
        sys.exit(ret)

    test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

    ret = codechecker.check(codechecker_cfg,
                            test_project_name,
                            project.path(test_project))

    if ret:
        sys.exit(1)
    print("Analyzing the test project was successful.")

    if pg_db_config:
        print("Waiting for PostgreSQL to stop.")
        codechecker.wait_for_postgres_shutdown(TEST_WORKSPACE)

    codechecker_cfg['run_names'] = [test_project_name]

    test_config['codechecker_cfg'] = codechecker_cfg

    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Start the CodeChecker server.
    print("Starting server to get results")
    _start_server(codechecker_cfg, test_config, False)


def teardown_package():
    """Stop the CodeChecker server."""
    __STOP_SERVER.set()

    # TODO: if environment variable is set keep the workspace
    # and print out the path
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)


def _start_server(codechecker_cfg, test_config, auth=False):
    """Start the CodeChecker server."""

    def start_server_proc(event, server_cmd, checking_env):
        """Target function for starting the CodeChecker server."""
        proc = subprocess.Popen(server_cmd, env=checking_env)

        # Blocking termination until event is set.
        event.wait()

        # If proc is still running, stop it.
        if proc.poll() is None:
            proc.terminate()

    server_cmd = codechecker.serv_cmd(codechecker_cfg, test_config)

    server_proc = multiprocessing.Process(
        name='server',
        target=start_server_proc,
        args=(__STOP_SERVER, server_cmd, codechecker_cfg['check_env']))

    server_proc.start()

    # Wait for server to start and connect to database.
    time.sleep(20)


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
