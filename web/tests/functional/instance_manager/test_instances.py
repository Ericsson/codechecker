#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Instance manager tests.
"""


import multiprocessing
import os
import shutil
import subprocess
import time
import unittest

from codechecker_server import instance_manager

from libtest import env
from libtest.codechecker import start_server

# Stopping events for CodeChecker servers.
EVENT_1 = multiprocessing.Event()
EVENT_2 = multiprocessing.Event()


class TestInstances(unittest.TestCase):
    """
    Server instance manager tests.
    """

    def setup_class(self):
        """Setup the environment for the tests then start the server."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('instances')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_env = env.test_env(TEST_WORKSPACE)

        # Setup environment variables for the test cases.
        host_port_cfg = {'viewer_host': 'localhost',
                         'viewer_port': env.get_free_port()}

        codechecker_cfg = {
            'workspace': TEST_WORKSPACE,
            'check_env': test_env,
            'run_names': [],
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }
        codechecker_cfg.update(host_port_cfg)
        test_config['codechecker_1'] = codechecker_cfg

        # We need a second server
        codechecker_cfg = {
            'workspace': TEST_WORKSPACE,
            'check_env': test_env,
            'run_names': [],
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }
        host_port_cfg = {'viewer_host': 'localhost',
                         'viewer_port': env.get_free_port()}

        if host_port_cfg['viewer_port'] == \
                test_config['codechecker_1']['viewer_port']:
            host_port_cfg['viewer_port'] = \
                int(host_port_cfg['viewer_port']) + 1

        codechecker_cfg.update(host_port_cfg)
        test_config['codechecker_2'] = codechecker_cfg

        # Export configuration for the tests.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

        # Wait for previous test instances to terminate properly and
        # clean the instance file in the user's home directory.
        time.sleep(5)

    def teardown_class(self):
        """Stop the CodeChecker server."""

        # Let the remaining CodeChecker servers die.
        EVENT_1.set()
        EVENT_2.set()

        # TODO If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):
        # Get the test workspace used to tests.
        self._test_workspace = os.environ['TEST_WORKSPACE']

        test_cfg = env.import_test_cfg(self._test_workspace)
        self._test_env = test_cfg['codechecker_1']['check_env']
        self.home = self._test_env['HOME']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

    def run_cmd(self, cmd):
        print(cmd)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            env=self._test_env,
            encoding="utf-8",
            errors="ignore")

        out, _ = proc.communicate()
        print(out)
        return proc.returncode

    def testServerStart(self):
        """Started server writes itself to instance list."""

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        EVENT_1.clear()
        start_server(codechecker_1, EVENT_1, ['--skip-db-cleanup'])

        instance = [i for i in instance_manager.get_instances(self.home)
                    if i['port'] == codechecker_1['viewer_port'] and
                    i['workspace'] == self._test_workspace]

        self.assertNotEqual(instance, [],
                            "The started server did not register itself to the"
                            " instance list.")

    def testServerStartSecondary(self):
        """Another started server appends itself to instance list."""

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        codechecker_2 = test_cfg['codechecker_2']
        EVENT_2.clear()
        start_server(codechecker_2, EVENT_2, ['--skip-db-cleanup'])

        # Workspaces must match, servers were started in the same workspace.
        instance_workspaces = [
            i['workspace'] for i in instance_manager.get_instances(self.home)
            if i['workspace'] == self._test_workspace]

        self.assertEqual(len(instance_workspaces), 2,
                         "Two servers in the same workspace but the workspace"
                         " was not found twice in the instance list.")

        # Exactly one server should own each port generated
        instance_ports = [
            i['port'] for i in instance_manager.get_instances(self.home)
            if i['port'] == codechecker_1['viewer_port'] or
            i['port'] == codechecker_2['viewer_port']]

        self.assertEqual(len(instance_ports), 2,
                         "The ports for the two started servers were not found"
                         " in the instance list.")

    def testShutdownRecordKeeping(self):
        """Test that one server's shutdown keeps the other records."""

        # NOTE: Do NOT rename this method. It MUST come lexicographically
        # AFTER testServerStartSecondary, because we shut down a server started
        # by the aforementioned method.

        # Kill the second started server.
        EVENT_2.set()

        # Give the server some grace period to react to the kill command.
        time.sleep(5)

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        codechecker_2 = test_cfg['codechecker_2']

        instance_1 = [i for i in instance_manager.get_instances(self.home)
                      if i['port'] == codechecker_1['viewer_port'] and
                      i['workspace'] == self._test_workspace]
        instance_2 = [i for i in instance_manager.get_instances(self.home)
                      if i['port'] == codechecker_2['viewer_port'] and
                      i['workspace'] == self._test_workspace]

        self.assertNotEqual(instance_1, [],
                            "The stopped server deleted another server's "
                            "record from the instance list!")

        self.assertEqual(instance_2, [],
                         "The stopped server did not disappear from the"
                         " instance list.")

    def testShutdownTerminateByCmdline(self):
        """Tests that the command-line command actually kills the server,
        and that it does not kill anything else."""

        # NOTE: Yet again keep the lexicographical flow, no renames!

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        codechecker_2 = test_cfg['codechecker_2']
        EVENT_2.clear()
        start_server(codechecker_2, EVENT_2, ['--skip-db-cleanup'])

        # Kill the server, but yet again give a grace period.
        self.assertEqual(0, self.run_cmd([env.codechecker_cmd(),
                                          'server', '--stop',
                                          '--view-port',
                                          str(codechecker_2['viewer_port']),
                                          '--workspace',
                                          self._test_workspace]),
                         "The stop command didn't return exit code 0.")

        # Check if the remaining server is still there,
        # we need to make sure that --stop only kills the specified server!
        instance_1 = [i for i in instance_manager.get_instances(self.home)
                      if i['port'] == codechecker_1['viewer_port'] and
                      i['workspace'] == self._test_workspace]
        instance_2 = [i for i in instance_manager.get_instances(self.home)
                      if i['port'] == codechecker_2['viewer_port'] and
                      i['workspace'] == self._test_workspace]

        self.assertNotEqual(instance_1, [],
                            "The stopped server deleted another server's "
                            "record from the instance list!")

        self.assertEqual(instance_2, [],
                         "The stopped server did not disappear from the"
                         " instance list.")

        # Kill the first server via cmdline too.
        self.assertEqual(0, self.run_cmd([env.codechecker_cmd(),
                                          'server', '--stop',
                                          '--view-port',
                                          str(codechecker_1['viewer_port']),
                                          '--workspace',
                                          self._test_workspace]),
                         "The stop command didn't return exit code 0.")

        instance_1 = [i for i in instance_manager.get_instances(self.home)
                      if i['port'] == codechecker_1['viewer_port'] and
                      i['workspace'] == self._test_workspace]
        instance_2 = [i for i in instance_manager.get_instances(self.home)
                      if i['port'] == codechecker_2['viewer_port'] and
                      i['workspace'] == self._test_workspace]

        self.assertEqual(instance_1, [],
                         "The stopped server did not disappear from the"
                         " instance list.")

        self.assertEqual(instance_2, [],
                         "The stopped server made another server's record "
                         "appear in the instance list.")

    def testShutdownTerminateStopAll(self):
        """Tests that --stop-all kills all servers on the host."""

        # NOTE: Yet again keep the lexicographical flow, no renames!

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        codechecker_2 = test_cfg['codechecker_2']
        EVENT_1.clear()
        EVENT_2.clear()
        start_server(codechecker_1, EVENT_1, ['--skip-db-cleanup'])
        start_server(codechecker_2, EVENT_2, ['--skip-db-cleanup'])

        self.assertEqual(len(instance_manager.get_instances(self.home)), 2,
                         "Two servers were started but they don't appear "
                         "in the instance list.")

        # Kill the servers via cmdline.
        self.assertEqual(0, self.run_cmd([env.codechecker_cmd(),
                                          'server', '--stop-all']),
                         "The stop-all command didn't return exit code 0.")

        self.assertEqual(len(instance_manager.get_instances(self.home)), 0,
                         "Both servers were allegedly stopped but they "
                         "did not disappear.")
