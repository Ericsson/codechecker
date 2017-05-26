#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Authentication tests.
"""
import os
import unittest

from thrift.protocol.TProtocol import TProtocolException

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

    def test_privileged_access(self):
        """
        Tests that initially, a non-authenticating server is accessible,
        but an authenticating one is not.
        """

        auth_client = env.setup_auth_client(self._test_workspace)
        handshake = auth_client.getAuthParameters()
        self.assertTrue(handshake.requiresAuthentication,
                        "Privileged server " +
                        "did not report that it requires authentication.")
        self.assertFalse(handshake.sessionStillActive, "Empty session was " +
                         "reported to be still active.")

        sessionToken = auth_client.performLogin("Username:Password",
                                                "invalid:invalid")
        self.assertIsNone(sessionToken, "Invalid credentials gave us a token!")

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

        self.assertIsNotNone(client.getAPIVersion(),
                             "Privileged server didn't respond properly.")

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token=self.sessionToken)
        result = auth_client.destroySession()

        self.assertTrue(result, "Server did not allow us to destroy session.")

        try:
            client.getAPIVersion()
            success = False
        except TProtocolException:
            # The server reports a HTTP 401 error which
            # is not a valid Thrift response.
            # But if it does so, it passes the test!
            success = True
        self.assertTrue(success,
                        "Privileged client allowed access after logout.")

        handshake = auth_client.getAuthParameters()
        self.assertFalse(handshake.sessionStillActive,
                         "Destroyed session was " +
                         "reported to be still active.")
