#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import multiprocessing
import os
import time
import unittest

from codechecker_lib import instance_manager

from . import get_free_port
from . import start_dummy_server

_Dummy_Event = multiprocessing.Event()


class RunResults(unittest.TestCase):
    def setUp(self):
        self.workspace = os.path.join(
            os.environ['TEST_CODECHECKER_PACKAGE_DIR'],
            "workspace")

    def test_instances_environment(self):
        """Tests that the running instances are properly added to the user's
        instance descriptor."""
        test_viewer = False
        auth_viewer = False

        instances = instance_manager.list()
        for i in instances:
            if i['port'] == int(os.environ['CC_TEST_VIEWER_PORT']) and \
                    i['workspace'] == self.workspace:
                test_viewer = True

            if i['port'] == int(os.environ['CC_AUTH_VIEWER_PORT']) and \
                    i['workspace'] == self.workspace:
                auth_viewer = True

        self.assertTrue(test_viewer and auth_viewer,
                        "Running CodeChecker server didn't register itself "
                        "into instance manager.")

    def test_instances_dummy(self):
        """Tests that a newly created instance registers and after shutdown,
        unregisters itself from the instance descriptor."""
        free_port = get_free_port()

        start_dummy_server(_Dummy_Event, self.workspace, free_port)

        # Check if the dummy server registered itself, and that the "real"
        # test servers are still in the list.
        test_viewer = False
        auth_viewer = False
        dummy_server = False

        instances = instance_manager.list()
        for i in instances:
            if i['port'] == int(os.environ['CC_TEST_VIEWER_PORT']) and \
                    i['workspace'] == self.workspace:
                test_viewer = True

            if i['port'] == int(os.environ['CC_AUTH_VIEWER_PORT']) and \
                    i['workspace'] == self.workspace:
                auth_viewer = True

            if i['port'] == free_port and i['workspace'] == self.workspace:
                dummy_server = True

        self.assertTrue(test_viewer, "The started dummy server removed the "
                                     "test server from the instance list.")
        self.assertTrue(auth_viewer, "The started dummy server removed the "
                                     "auth-enabled server from the instance "
                                     "list.")
        self.assertTrue(dummy_server, "The started dummy server did not "
                                      "register itself into the instance "
                                      "list.")

        # Now kill the dummy server, wait for it to die, then see if it
        # unregistered itself or not.
        _Dummy_Event.set()
        time.sleep(5)

        test_viewer = False
        auth_viewer = False
        dummy_server = False

        instances = instance_manager.list()
        for i in instances:
            if i['port'] == int(os.environ['CC_TEST_VIEWER_PORT']) and \
                    i['workspace'] == self.workspace:
                test_viewer = True

            if i['port'] == int(os.environ['CC_AUTH_VIEWER_PORT']) and \
                    i['workspace'] == self.workspace:
                auth_viewer = True

            if i['port'] == free_port and i['workspace'] == self.workspace:
                dummy_server = True

        self.assertTrue(test_viewer, "The stopping dummy server removed the "
                                     "test server from the instance list.")
        self.assertTrue(auth_viewer, "The stopping dummy server removed the "
                                     "auth-enabled server from the instance "
                                     "list.")
        self.assertFalse(dummy_server, "The stopping dummy server did not "
                                       "remove itself from the instance "
                                       "list.")
