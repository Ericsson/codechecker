# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
server_configuration function test.
"""


import os
import shutil
import unittest

from codechecker_api_shared.ttypes import Permission
from codechecker_api_shared.ttypes import RequestFailed

from codechecker_web.shared import convert

from libtest import codechecker
from libtest import env


class ConfigTests(unittest.TestCase):

    _ccClient = None

    def setup_class(self):
        """Setup the environment for testing server_configuration."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('server_configuration')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        # Get an environment which should be used by the tests.
        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server(auth_required=True)
        server_access['viewer_product'] = 'server_configuration'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Save the run names in the configuration.
        codechecker_cfg['run_names'] = []

        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, _):
        """
        Setup Configuration for tests.
        """

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self._test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        self.auth_client = env.setup_auth_client(self._test_workspace,
                                                 session_token='_PROHIBIT')

        self.config_client = env.setup_config_client(self._test_workspace,
                                                     session_token='_PROHIBIT')

    def test_noauth_notification_edit(self):
        """
        Test for editing the notification text on a non authenting server.
        """

        # A non-authenticated session should return an empty user.
        user = self.auth_client.getLoggedInUser()
        self.assertEqual(user, "")

        # Server without authentication should allow notification setting.
        self.config_client.setNotificationBannerText(
            convert.to_b64('noAuth notif'))
        self.assertEqual(convert.from_b64(
            self.config_client.getNotificationBannerText()), 'noAuth notif')

    def test_auth_su_notification_edit(self):
        """
        Test that SUPERADMINS can edit the notification text.
        """
        # Create a SUPERUSER login.
        self.session_token = self.auth_client.performLogin(
            "Username:Password", "root:root")

        ret = self.auth_client.addPermission(Permission.SUPERUSER,
                                             "root",
                                             False,
                                             "")
        self.assertTrue(ret)
        # we got the permission

        su_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.session_token)

        su_config_client = \
            env.setup_config_client(self._test_workspace,
                                    session_token=self.session_token)

        user = su_auth_client.getLoggedInUser()
        self.assertEqual(user, "root")
        # we are root

        su_config_client.setNotificationBannerText(
                convert.to_b64('su notification'))
        self.assertEqual(convert.from_b64(
            su_config_client.getNotificationBannerText()),
                'su notification')

    def test_auth_non_su_notification_edit(self):
        """
        Test that non SUPERADMINS can't edit the notification text.
        """
        self.session_token = self.auth_client.performLogin(
            "Username:Password", "cc:test")

        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.session_token)

        authd_config_client = \
            env.setup_config_client(self._test_workspace,
                                    session_token=self.session_token)

        user = authd_auth_client.getLoggedInUser()
        self.assertEqual(user, "cc")

        with self.assertRaises(RequestFailed):
            authd_config_client.setNotificationBannerText(
                    convert.to_b64('non su notification'))

            print("You are not authorized to modify notifications!")

    def test_unicode_string(self):
        """
        Test for non ascii strings. Needed because the used Thrift
        version won't eat them.
        """

        # A non-authenticated session should return an empty user.
        user = self.auth_client.getLoggedInUser()
        self.assertEqual(user, "")

        # Check if utf-8 encoded strings are okay.
        self.config_client.setNotificationBannerText(
                convert.to_b64('árvíztűrő tükörfúrógép'))
        self.assertEqual(convert.from_b64(
            self.config_client.getNotificationBannerText()),
            'árvíztűrő tükörfúrógép')
