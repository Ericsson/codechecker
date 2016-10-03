#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import json
import logging
import os
import re
import unittest

from thrift.protocol.TProtocol import TProtocolException

from test_utils.thrift_client_to_db import CCViewerHelper
from test_utils.thrift_client_to_db import CCAuthHelper

class RunResults(unittest.TestCase):
    def setUp(self):
        self.host = 'localhost'
        self.port = int(os.environ['CC_AUTH_VIEWER_PORT'])
        self.uri = '/Authentication'

    def test_initial_access(self):
        """Tests that initially, a non-authenticating server is accessible,
        but an authenticating one is not."""
        client_unprivileged = CCViewerHelper(self.host,int(
            os.environ['CC_TEST_VIEWER_PORT']), '/', True, None)
        client_privileged = CCViewerHelper(self.host, self.port, '/', True, None)

        self.assertIsNotNone(client_unprivileged.getAPIVersion(),
                             "Unprivileged client was not accessible.")

        try:
            client_privileged.getAPIVersion()
            success = False
        except TProtocolException as tpe:
            # The server reports a HTTP 401 error which is not a valid Thrift response
            # But if it does so, it passes the test!
            success = True
        self.assertTrue(success, "Privileged client allowed access without session.")

    def test_privileged_access(self):
        """Tests that initially, a non-authenticating server is accessible,
        but an authenticating one is not."""
        auth_client = CCAuthHelper(self.host, self.port, self.uri, True, None)

        handshake = auth_client.getAuthParameters()
        self.assertTrue(handshake.requiresAuthentication, "Privileged server " +
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
        self.assertTrue(handshake.requiresAuthentication, "Privileged server " +
                        "did not report that it requires authentication.")
        self.assertFalse(handshake.sessionStillActive, "Valid session was " +
                         "reported not to be active.")

        client = CCViewerHelper(self.host, self.port, '/', True, self.sessionToken)

        self.assertIsNotNone(client.getAPIVersion(),
                             "Privileged server didn't respond properly.")

        auth_client = CCAuthHelper(self.host, self.port, self.uri, True,
                                   self.sessionToken)
        result = auth_client.destroySession()

        self.assertTrue(result, "Server did not allow us to destroy session.")

        try:
            client.getAPIVersion()
            success = False
        except TProtocolException as tpe:
            # The server reports a HTTP 401 error which is not a valid Thrift response
            # But if it does so, it passes the test!
            success = True
        self.assertTrue(success, "Privileged client allowed access after logout.")

        handshake = auth_client.getAuthParameters()
        self.assertFalse(handshake.sessionStillActive, "Destroyed session was " +
                         "reported to be still active.")


