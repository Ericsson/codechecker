#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import subprocess
import time
import unittest

from libcodechecker.server import instance_manager

from libtest import env
from . import EVENT_1, EVENT_2, EVENT_3
from . import start_server

"""
Instance manager tests.
"""


def run_cmd(cmd):
    print(cmd)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE)

    out, _ = proc.communicate()
    print(out)
    return proc.returncode


class Instances(unittest.TestCase):
    """
    Server instance manager tests.
    """

    def setUp(self):
        # Get the test workspace used to tests.
        self._test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

    def testInitialFile(self):
        """Tests that initially az instance file is created."""

        self.assertEqual(instance_manager.list(), [],
                         "The initial instance file was not empty initially.")

    def testServerStart(self):
        """Started server writes itself to instance list."""

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        start_server(codechecker_1, test_cfg, EVENT_1)

        self.assertEqual(len(instance_manager.list()), 1,
                         "The started server was not appended to the "
                         "instance list.")

        self.assertEqual(instance_manager.list()[0]['port'],
                         codechecker_1['viewer_port'],
                         "The written port in the instance list is not the "
                         "one the server was started with!")

        self.assertEqual(instance_manager.list()[0]['workspace'],
                         self._test_workspace,
                         "Server was brought up with invalid workspace.")

    def testServerStartSecondary(self):
        """Another started server appends itself to instance list."""

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        codechecker_2 = test_cfg['codechecker_2']
        start_server(codechecker_2, test_cfg, EVENT_2)

        self.assertEqual(len(instance_manager.list()), 2,
                         "The started server was not appended to the "
                         "instance list.")

        # Workspaces must match, servers were started in the same workspace.
        instance_workspaces = [i['workspace'] for i in instance_manager.list()]
        self.assertEqual(instance_workspaces[0], self._test_workspace,
                         "Server was brought up with invalid workspace.")
        self.assertEqual(instance_workspaces[0], instance_workspaces[1],
                         "Server was brought up with invalid workspace.")

        # Exactly one server should own each port generated
        instance_ports = [i['port'] for i in instance_manager.list()]

        self.assertTrue(codechecker_1['viewer_port'] in instance_ports,
                        "Missing port for server started earlier!")

        self.assertTrue(codechecker_2['viewer_port'] in instance_ports,
                        "Missing port for server started later!")

        self.assertEqual(len(set(instance_ports)), 2,
                         "The servers started with the same port.")

    def testShutdownRecordKeeping(self):
        """Test that one server's shutdown keeps the other records."""

        # NOTE: Do NOT rename this method. It MUST come lexicographically
        # AFTER testServerStartSecondary, because we shut down a server started
        # by the aforementioned method.

        self.assertEqual(len(instance_manager.list()), 2,
                         "The server disappeared from the instance list "
                         "before shutdown.")

        # Kill the second started server.
        EVENT_2.set()

        # Give the server some grace period to react to the kill command.
        time.sleep(5)

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']

        self.assertEqual(len(instance_manager.list()), 1,
                         "The server did not disappear from the "
                         "instance list.")

        self.assertEqual(instance_manager.list()[0]['port'],
                         codechecker_1['viewer_port'],
                         "The written port in the instance list is not the "
                         "one the server was started with!")

        self.assertEqual(instance_manager.list()[0]['workspace'],
                         self._test_workspace,
                         "Server was brought up with invalid workspace.")

    def testShutdownTerminateByCmdline(self):
        """Tests that the command-line command actually kills the server,
        and that it does not kill anything else."""

        # NOTE: Yet again keep the lexicographical flow, no renames!

        test_cfg = env.import_test_cfg(self._test_workspace)
        codechecker_1 = test_cfg['codechecker_1']
        codechecker_2 = test_cfg['codechecker_2']
        start_server(codechecker_2, test_cfg, EVENT_3)

        self.assertEqual(len(instance_manager.list()), 2,
                         "The started server was not appended to the "
                         "instance list.")

        # Kill the server, but yet again give a grace period.
        self.assertEqual(0, run_cmd([env.codechecker_cmd(),
                                     'server', '--stop',
                                     '--view-port',
                                     str(codechecker_2['viewer_port']),
                                     '--workspace',
                                     self._test_workspace]),
                         "The stop command didn't return exit code 0.")
        time.sleep(5)

        # Check if the remaining server is still there,
        # we need to make sure that --stop only kills the specified server!
        self.assertEqual(len(instance_manager.list()), 1,
                         "The server did not disappear from the "
                         "instance list.")

        self.assertEqual(instance_manager.list()[0]['port'],
                         codechecker_1['viewer_port'],
                         "The written port in the instance list is not the "
                         "one the server was started with!")

        self.assertEqual(instance_manager.list()[0]['workspace'],
                         self._test_workspace,
                         "Server was brought up with invalid workspace.")

        # Kill the first server via cmdline too.
        self.assertEqual(0, run_cmd([env.codechecker_cmd(),
                                     'server', '--stop',
                                     '--view-port',
                                     str(codechecker_1['viewer_port']),
                                     '--workspace',
                                     self._test_workspace]),
                         "The stop command didn't return exit code 0.")
        time.sleep(5)

        self.assertEqual(instance_manager.list(), [],
                         "The instance file didn't return to empty list "
                         "after all servers were killed.")
