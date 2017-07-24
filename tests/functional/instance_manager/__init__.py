# coding=utf-8
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Setup for the package tests."""

import copy
import json
import multiprocessing
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from subprocess import CalledProcessError

from libtest import get_free_port
from libtest import project
from libtest import codechecker
from libtest import env

# Stopping events for CodeChecker servers.
EVENT_1 = multiprocessing.Event()
EVENT_2 = multiprocessing.Event()

# Test workspace initialized at setup for authentication tests.
TEST_WORKSPACE = None


def setup_package():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('instances')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    # Setup environment varaibled for the test cases.
    host_port_cfg = env.get_host_port_cfg()

    codechecker_cfg = {
        'workspace': TEST_WORKSPACE,
        'run_names': [],
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)

    test_config['codechecker_1'] = codechecker_cfg

    # We need a second server
    codechecker_cfg = {
        'workspace': TEST_WORKSPACE,
        'run_names': [],
        'checkers': []
    }
    host_port_cfg = env.get_host_port_cfg()
    if host_port_cfg['viewer_port'] == \
            test_config['codechecker_1']['viewer_port']:
        host_port_cfg['viewer_port'] = int(host_port_cfg['viewer_port']) + 1
    codechecker_cfg.update(host_port_cfg)
    test_config['codechecker_2'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Wait for previous test instances to terminate properly and
    # clean the instance file in the user's home directory.
    time.sleep(5)


def teardown_package():
    """Stop the CodeChecker server."""

    # Let the remaining CodeChecker servers die.
    EVENT_1.set()
    EVENT_2.set()

    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE)


def start_server(codechecker_cfg, test_config, event):
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
        args=(event, server_cmd, env.test_env()))

    server_proc.start()
    # Wait for server to start and connect to database.
    time.sleep(15)
