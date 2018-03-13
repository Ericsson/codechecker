# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Unit tests for the credentials module. """

import unittest

from libcodechecker.libclient import credential_manager


class CredentialsTest(unittest.TestCase):
    """
    Testing the credentials.
    """

    def test_get_auth_string(self):
        """
        Get authentication string from the credentials.
        """
        credentials = {
            "client_autologin": True,
            "credentials": {
                "*": "global:passphrase",
                "*:8080": "webserver:1234",
                "localhost": "local:admin",
                "https://localhost/Test": "local1:admin1",
                "localhost:6251": "super:secret",
                "https://myserver.com/Test": "serveruser:serverpassphrase",
                "https://some.server.com:12345/Product": "user:secretpwd"}}

        tokens = {}
        credentials_mgr = credential_manager.UserCredentials(credentials,
                                                             tokens)

        self.assertTrue(credentials_mgr.is_autologin_enabled())

        self.assertEquals(credentials_mgr.get_auth_string('*', None),
                          "global:passphrase")
        self.assertEquals(credentials_mgr.get_auth_string('*', '8080'),
                          "webserver:1234")

        # Only first match localhost entry will be returned.
        self.assertEquals(credentials_mgr.get_auth_string('localhost', None),
                          "local:admin")
        self.assertEquals(credentials_mgr.get_auth_string('localhost', '6251'),
                          "super:secret")

        # Hostname needs to be provided without protocol
        self.assertEquals(
            credentials_mgr.get_auth_string('http://myserver.com', None),
            "global:passphrase")
        # Hostname needs to be provided without protocol
        self.assertEquals(
            credentials_mgr.get_auth_string('https://myserver.com', None),
            "global:passphrase")
        self.assertEquals(
            credentials_mgr.get_auth_string('myserver.com', None),
            "serveruser:serverpassphrase")

        self.assertEquals(
            credentials_mgr.get_auth_string('some.server.com', '12345'),
            "user:secretpwd")
        self.assertEquals(
            credentials_mgr.get_auth_string('some.server.com', None),
            "user:secretpwd")

    def test_get_auth_string_no_match(self):
        """
        Missing authentication string from the credentials.
        """
        credentials = {
            "client_autologin": True,
            "credentials": {
                "https://myserver.com/Test": "serveruser:serverpassphrase",
                "https://some.server.com:12345/Product": "user:secretpwd"}}

        tokens = {}
        credentials_mgr = credential_manager.UserCredentials(credentials,
                                                             tokens)

        self.assertIsNone(
            credentials_mgr.get_auth_string('dummy.server.com', None))
