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
import subprocess
import sys

from libtest import codechecker
from libtest import env
from time import sleep
import multiprocess

# Stopping event for CodeChecker server.
__STOP_SERVER = multiprocess.Event()

# OAuth mock server process.
__OAUTH_SERVER = None

# Test workspace initialized at setup for authentication tests.
TEST_WORKSPACE = None


def setup_class_common():
    """Setup the environment for the tests then start the server."""

    global TEST_WORKSPACE
    TEST_WORKSPACE = env.get_workspace('authentication')

    os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    test_config = {}

    # Setup environment variables for the test cases.
    host_port_cfg = {'viewer_host': 'localhost',
                     'viewer_port': env.get_free_port(),
                     'viewer_product': 'authentication'}

    test_env = env.test_env(TEST_WORKSPACE)

    codechecker_cfg = {
        'check_env': test_env,
        'workspace': TEST_WORKSPACE,
        'checkers': []
    }

    codechecker_cfg.update(host_port_cfg)

    codechecker_cfg['run_names'] = []

    test_config['codechecker_cfg'] = codechecker_cfg

    # Export configuration for the tests.
    env.export_test_cfg(TEST_WORKSPACE, test_config)

    # Enable authentication and start the CodeChecker server.
    env.enable_auth(TEST_WORKSPACE)

    print("Starting server to get results")
    codechecker.start_server(codechecker_cfg, __STOP_SERVER)

    codechecker.add_test_package_product(host_port_cfg, TEST_WORKSPACE)

    subprocess.run(["pkill", "-f", "oauth_server.py"],
                   capture_output=True, check=False)
    sleep(1)

    global __OAUTH_SERVER
    oauth_log = os.path.join(TEST_WORKSPACE, "oauth_server.log")
    oauth_out = open(oauth_log, "w", encoding="utf-8")
    __OAUTH_SERVER = subprocess.Popen(
        [sys.executable, "oauth_server.py"],
        cwd="tests/functional/authentication",
        stdout=oauth_out,
        stderr=oauth_out)

    # Wait for mock server to be ready (port 3000 open).
    import socket
    ready = False
    for i in range(30):
        try:
            s = socket.create_connection(("127.0.0.1", 3000), timeout=1)
            s.close()
            ready = True
            print(f"OAuth mock server ready after {i+1}s")
            break
        except (ConnectionRefusedError, OSError):
            if __OAUTH_SERVER.poll() is not None:
                oauth_out.flush()
                with open(oauth_log, encoding="utf-8") as f:
                    print(f"OAuth mock server DIED "
                          f"(rc={__OAUTH_SERVER.returncode}): "
                          f"{f.read()}")
                break
            sleep(1)

    if not ready:
        oauth_out.flush()
        with open(oauth_log, encoding="utf-8") as f:
            print(f"OAuth mock server NOT ready after 30s. "
                  f"Log: {f.read()}")
        print(f"OAuth server poll: {__OAUTH_SERVER.poll()}")


def teardown_class_common():
    """Stop the CodeChecker server and clean up after the tests."""
    # TODO If environment variable is set keep the workspace
    # and print out the path.
    global TEST_WORKSPACE
    global __OAUTH_SERVER

    if __OAUTH_SERVER:
        __OAUTH_SERVER.terminate()
        __OAUTH_SERVER.wait()
        __OAUTH_SERVER = None

    # Removing the product through this server requires credentials.
    codechecker_cfg = env.import_test_cfg(TEST_WORKSPACE)['codechecker_cfg']
    codechecker.remove_test_package_product(TEST_WORKSPACE,
                                            codechecker_cfg['check_env'])

    __STOP_SERVER.set()
    __STOP_SERVER.clear()

    print("Removing: " + TEST_WORKSPACE)
    shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)
