# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Unit tests for the credentials module. """

import unittest

from codechecker_client.credential_manager import simplify_credentials


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
                "localhost:6251": "super:secret",
                "https://localhost:443/Test": "local1:admin1",
                "https://myserver.com/Test": "serveruser:serverpassphrase",
                "https://some.server.com:12345/Product": "user:secretpwd"}}

        # Replace the key of the entries with host:port values.
        cred_simple = simplify_credentials(credentials["credentials"])

        self.assertIn('*', cred_simple)
        self.assertIn('*:8080', cred_simple)
        self.assertIn('localhost', cred_simple)
        self.assertIn('localhost:6251', cred_simple)
        self.assertIn('localhost:443', cred_simple)
        self.assertIn('myserver.com', cred_simple)
        self.assertIn('some.server.com:12345', cred_simple)
