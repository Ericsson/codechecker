#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Authentication tests.
"""


import json
import os
import subprocess
import unittest

from codechecker_api_shared.ttypes import RequestFailed, Permission

from codechecker_client.credential_manager import UserCredentials
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

        with self.assertRaises(RequestFailed):
            auth_client.performLogin("Username:Password", None)

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

        self.sessionToken = auth_client.performLogin("Username:Password",
                                                     "colon:my:password")
        self.assertIsNotNone(self.sessionToken,
                             "Valid credentials didn't give us a token!")

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

    def test_group_auth(self):
        """
        Test for case insensitive group comparison at authorization.
        """
        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')

        # A non-authenticated session should return an empty user.
        user = auth_client.getLoggedInUser()
        self.assertEqual(user, "")

        # Create a SUPERUSER login.
        self.sessionToken = auth_client.performLogin("Username:Password",
                                                     "root:root")

        self.assertIsNotNone(self.sessionToken,
                             "Valid credentials didn't give us a token!")

        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.sessionToken)
        user = authd_auth_client.getLoggedInUser()
        self.assertEqual(user, "root")

        product_name = self._test_cfg['codechecker_cfg']['viewer_product']
        pr_client = env.setup_product_client(
            self._test_workspace, product=product_name)
        product_id = pr_client.getCurrentProduct().id

        extra_params = {'productID': product_id}
        ret = authd_auth_client.addPermission(Permission.PRODUCT_ADMIN,
                                              "ADMIN_group",
                                              True,
                                              json.dumps(extra_params))
        self.assertTrue(ret)

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Perform login with a user who is in ADMIN_GROUP and check that
        # he has permission to perform operations.
        self.sessionToken = \
            auth_client.performLogin("Username:Password",
                                     "admin_group_user:admin123")

        self.assertIsNotNone(self.sessionToken,
                             "Valid credentials didn't give us a token!")

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=self.sessionToken)

        self.assertIsNotNone(client.allowsStoringAnalysisStatistics(),
                             "Privileged server didn't respond properly.")

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

    def test_regex_groups(self):
        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')
        # First login as root.
        self.sessionToken = auth_client.performLogin("Username:Password",
                                                     "root:root")
        self.assertIsNotNone(self.sessionToken,
                             "root was unable to login!")

        # Then give SUPERUSER privs to admins_custom_group.
        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.sessionToken)
        ret = authd_auth_client.addPermission(Permission.SUPERUSER,
                                              "admins_custom_group",
                                              True, None)
        self.assertTrue(ret)

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Login as a user who is in admins_custom_group.
        sessionToken = auth_client.performLogin("Username:Password",
                                                "regex_admin:blah")
        self.assertIsNotNone(sessionToken,
                             "Valid credentials didn't give us a token!")

        # Do something privileged.
        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=sessionToken)
        self.assertIsNotNone(client.allowsStoringAnalysisStatistics(),
                             "Privileged call failed.")

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Finally try to do the same with an unprivileged user.
        sessionToken = auth_client.performLogin("Username:Password",
                                                "john:doe")
        self.assertIsNotNone(sessionToken,
                             "Valid credentials didn't give us a token!")

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=sessionToken)
        self.assertFalse(client.allowsStoringAnalysisStatistics(),
                         "Privileged call from unprivileged user"
                         " did not fail!")

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

    def test_personal_access_tokens(self):
        """ Test personal access token commands. """
        codechecker_cfg = self._test_cfg['codechecker_cfg']
        host = codechecker_cfg['viewer_host']
        port = codechecker_cfg['viewer_port']

        new_token_cmd = [env.codechecker_cmd(), 'cmd', 'token', 'new',
                         '--url', env.parts_to_url(codechecker_cfg)]

        with self.assertRaises(subprocess.CalledProcessError):
            subprocess.check_output(
                new_token_cmd,
                encoding="utf-8",
                errors="ignore")

        # Login to the server.
        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')

        # A non-authenticated session should return an empty user.
        user = auth_client.getLoggedInUser()
        self.assertEqual(user, "")

        # Create a SUPERUSER login.
        session_token = auth_client.performLogin("Username:Password",
                                                 "cc:test")

        self.assertIsNotNone(session_token,
                             "Valid credentials didn't give us a token!")

        cred_manager = UserCredentials()
        cred_manager.save_token(host, port, session_token)

        # Run the new token command after login.
        subprocess.check_output(
            new_token_cmd,
            encoding="utf-8",
            errors="ignore")

        # List personal access tokens.
        list_token_cmd = [env.codechecker_cmd(), 'cmd', 'token', 'list',
                          '--url', env.parts_to_url(codechecker_cfg),
                          '-o', 'json']

        out_json = subprocess.check_output(
            list_token_cmd, encoding="utf-8", errors="ignore")
        tokens = json.loads(out_json)
        self.assertEqual(len(tokens), 1)

        # Remove personal access token.
        del_token_cmd = [env.codechecker_cmd(), 'cmd', 'token', 'del',
                         '--url', env.parts_to_url(codechecker_cfg),
                         tokens[0]['token']]

        subprocess.check_output(
            del_token_cmd,
            encoding="utf-8",
            errors="ignore")

        cred_manager.save_token(host, port, session_token, True)
