#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Authentication tests.
"""
import json
import os
import subprocess
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

        tcfg = os.path.join(self._test_workspace, 'test_config.json')
        with open(tcfg, 'r') as cfg:
            t = json.load(cfg)
            self._host = t['codechecker_cfg']['viewer_host']
            self._port = t['codechecker_cfg']['viewer_port']

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

        # A non-authenticated session should return an empty user.
        user = auth_client.getLoggedInUser()
        self.assertEqual(user, "")

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

        authd_auth_client =\
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.sessionToken)
        user = authd_auth_client.getLoggedInUser()
        self.assertEqual(user, "cc")

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

    def test_nonauth_storage(self):
        """
        Storing the result should fail.
        Authentication is required by the server but before the
        store command there was no login so storing the report should fail.
        """

        test_dir = os.path.dirname(os.path.realpath(__file__))
        report_file = os.path.join(test_dir, 'clang-5.0-trunk.plist')

        store_cmd = [env.codechecker_cmd(), 'store', '--name', 'auth',
                     '--host', str(self._host), '--port', str(self._port),
                     report_file]

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output(store_cmd)
