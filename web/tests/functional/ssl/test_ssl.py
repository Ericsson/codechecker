#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
SSL test.
"""


import os
import subprocess
import unittest

from codechecker_api_shared.ttypes import RequestFailed

from libtest import codechecker
from libtest import env


class TestSSL(unittest.TestCase):
    """
    Test SSL layering on the server.
    """

    def setUp(self):

        # Get the test workspace used to authentication tests.
        self._test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._test_cfg = env.import_test_cfg(self._test_workspace)

    def test_privileged_access(self):
        """
        Tests that initially, a non-authenticating server is accessible,
        but an authenticating one is not.
        """

        # Switch off certificate validation on the clients.
        os.environ["OSPYTHONHTTPSVERIFY"] = '0'
        # FIXME: change this to https
        access_protocol = 'http'

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT',
                                            proto=access_protocol)
        handshake = auth_client.getAuthParameters()
        self.assertTrue(handshake.requiresAuthentication,
                        "Privileged server " +
                        "did not report that it requires authentication.")
        self.assertFalse(handshake.sessionStillActive, "Empty session was " +
                         "reported to be still active.")

        with self.assertRaises(RequestFailed):
            auth_client.performLogin("Username:Password", "invalid:invalid")
            print("Invalid credentials gave us a token!")

        # A non-authenticated session should return an empty user.
        user = auth_client.getLoggedInUser()
        self.assertEqual(user, "")

        # We still need to create a product on the new server, because
        # in PostgreSQL mode, the same database is used for configuration
        # by the newly started instance of this test suite too.
        codechecker.add_test_package_product(
            self._test_cfg['codechecker_cfg'],
            self._test_workspace,
            # Use the test's home directory to find the session token file.
            self._test_cfg['codechecker_cfg']['check_env'],
            access_protocol)

        self.sessionToken = auth_client.performLogin("Username:Password",
                                                     "cc:test")
        self.assertIsNotNone(self.sessionToken,
                             "Valid credentials didn't give us a token!")

        handshake = auth_client.getAuthParameters()
        self.assertTrue(handshake.requiresAuthentication,
                        "Privileged server " +
                        "did not report that it requires authentication.")
        self.assertFalse(handshake.sessionStillActive,
                         "Valid session was " + "reported not to be active.")

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=self.sessionToken,
                                         proto=access_protocol)

        self.assertIsNotNone(client.getPackageVersion(),
                             "Privileged server didn't respond properly.")

        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.sessionToken,
                                  proto=access_protocol)
        user = authd_auth_client.getLoggedInUser()
        self.assertEqual(user, "cc")

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token=self.sessionToken,
                                            proto=access_protocol)
        result = auth_client.destroySession()

        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Kill the session token that was created by login() too.
        codechecker.logout(self._test_cfg['codechecker_cfg'],
                           self._test_workspace,
                           access_protocol)

        # The server reports a HTTP 401 error which is not a valid
        # Thrift response. But if it does so, it passes the test!
        # FIXME: Because of the local session cache this check will fail.
        #        To enable this again we need to eliminate the local cache.
        # version = client.getPackageVersion()
        # self.assertIsNone(version,
        #                   "Privileged client allowed access after logout.")

        # handshake = auth_client.getAuthParameters()
        # self.assertFalse(handshake.sessionStillActive,
        #                  "Destroyed session was " +
        #                  "reported to be still active.")

        codechecker.remove_test_package_product(
            self._test_workspace,
            # Use the test's home directory to find the session token file.
            self._test_cfg['codechecker_cfg']['check_env'],
            access_protocol)

    def test_nonauth_storage(self):
        """
        Storing the result should fail.
        Authentication is required by the server but before the
        store command there was no login so storing the report should fail.
        """

        test_dir = os.path.dirname(os.path.realpath(__file__))
        report_file = os.path.join(test_dir, 'clang-5.0-trunk.plist')

        codechecker_cfg = self._test_cfg['codechecker_cfg']

        store_cmd = [env.codechecker_cmd(), 'store', '--name', 'auth',
                     # Use the 'Default' product.
                     '--url', env.parts_to_url(codechecker_cfg),
                     report_file]

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output(
                store_cmd, encoding="utf-8", errors="ignore")
