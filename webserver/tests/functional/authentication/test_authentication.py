#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Authentication tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os
import subprocess
import unittest

from thrift.protocol.TProtocol import TProtocolException

from shared.ttypes import RequestFailed

from libtest import codechecker
from libtest import env


class DictAuth(unittest.TestCase):
    """
    Dictionary based authentication tests.
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

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')
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
            self._test_cfg['codechecker_cfg']['check_env'])

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
                                         session_token=self.sessionToken)

        self.assertIsNotNone(client.getPackageVersion(),
                             "Privileged server didn't respond properly.")

        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.sessionToken)
        user = authd_auth_client.getLoggedInUser()
        self.assertEqual(user, "cc")

        # No personal token in the database.
        personal_tokens = authd_auth_client.getTokens()
        self.assertEqual(len(personal_tokens), 0)

        # Create a new personal token.
        description = "description"
        personal_token = authd_auth_client.newToken(description)
        token = personal_token.token
        self.assertEqual(personal_token.description, description)

        # Check whether the new token has been added.
        personal_tokens = authd_auth_client.getTokens()
        self.assertEqual(len(personal_tokens), 1)
        self.assertEqual(personal_tokens[0].token, token)
        self.assertEqual(personal_tokens[0].description, description)

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token=self.sessionToken)
        result = auth_client.destroySession()

        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Kill the session token that was created by login() too.
        codechecker.logout(self._test_cfg['codechecker_cfg'],
                           self._test_workspace)

        auth_token_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=token)

        # Log-in by using an already generated personal token.
        self.sessionToken = auth_token_client.performLogin("Username:Password",
                                                           "cc:" + token)

        self.assertIsNotNone(self.sessionToken,
                             "Valid credentials didn't give us a token!")

        user = auth_token_client.getLoggedInUser()
        self.assertEqual(user, "cc")

        result = auth_token_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Kill the session token that was created by login() too.
        codechecker.logout(self._test_cfg['codechecker_cfg'],
                           self._test_workspace)

        self.sessionToken = auth_client.performLogin("Username:Password",
                                                     "cc:test")
        self.assertIsNotNone(self.sessionToken,
                             "Valid credentials didn't give us a token!")

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token=self.sessionToken)
        # Remove the generated personal token.
        ret = auth_client.removeToken(token)
        self.assertTrue(ret)

        # Check whether no more personal token in the database.
        personal_tokens = auth_client.getTokens()
        self.assertEqual(len(personal_tokens), 0)

        result = auth_client.destroySession()

        self.assertTrue(result, "Server did not allow us to destroy session.")

        with self.assertRaises(TProtocolException):
            # The server reports a HTTP 401 error which is not a valid
            # Thrift response. But if it does so, it passes the test!
            client.getPackageVersion()
            print("Privileged client allowed access after logout.")

        handshake = auth_client.getAuthParameters()
        self.assertFalse(handshake.sessionStillActive,
                         "Destroyed session was " +
                         "reported to be still active.")

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
            subprocess.check_output(store_cmd)
