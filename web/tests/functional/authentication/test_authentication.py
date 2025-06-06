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
import io
import contextlib
import subprocess
import unittest
import requests

from codechecker_api_shared.ttypes import RequestFailed, Permission

from datetime import datetime, timedelta
from codechecker_server.session_manager \
    import SessionManager as SessMgr

from codechecker_client.credential_manager import UserCredentials
from codechecker_web.shared import convert
from libtest import codechecker
from libtest import env

from . import setup_class_common, teardown_class_common


class DictAuth(unittest.TestCase):
    """
    Dictionary based authentication tests.
    """

    def setup_class(self):
        setup_class_common()

    def teardown_class(self):
        teardown_class_common()

    def setup_method(self, _):
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
            print("Empty credentials gave us a token!")

        # A non-authenticated session should return an empty user.
        user = auth_client.getLoggedInUser()
        self.assertEqual(user, "")

        self.session_token = auth_client.performLogin(
            "Username:Password", "cc:test")
        self.assertIsNotNone(self.session_token,
                             "Valid credentials didn't give us a token!")

        handshake = auth_client.getAuthParameters()
        self.assertTrue(handshake.requiresAuthentication,
                        "Privileged server " +
                        "did not report that it requires authentication.")
        self.assertFalse(handshake.sessionStillActive,
                         "Valid session was " + "reported not to be active.")

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=self.session_token)

        self.assertIsNotNone(client.getPackageVersion(),
                             "Privileged server didn't respond properly.")

        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.session_token)
        user = authd_auth_client.getLoggedInUser()
        self.assertEqual(user, "cc")

        # No personal token in the database.
        personal_tokens = authd_auth_client.getPersonalAccessTokens()
        self.assertEqual(len(personal_tokens), 0)

        # Create a new personal token.
        description = "description"
        name = "name"
        expiration = 7
        exp_expiry_date = datetime.today() + timedelta(days=expiration)
        exp_expiry_date_str = exp_expiry_date.strftime("%Y-%m-%d %H:%M:%S")
        personal_token = authd_auth_client.newPersonalAccessToken(
            name, description, expiration)
        act_expiry_date_str = personal_token.expiration.split('.')[0]
        token = personal_token.token
        self.assertEqual(personal_token.description, description)
        self.assertEqual(act_expiry_date_str, exp_expiry_date_str)

        # Check whether the new token has been added.
        personal_tokens = authd_auth_client.getPersonalAccessTokens()
        self.assertEqual(len(personal_tokens), 1)
        self.assertEqual(personal_tokens[0].token, "")
        self.assertEqual(personal_tokens[0].name, name)
        self.assertEqual(personal_tokens[0].description, description)
        pers_token_expiry_str = personal_tokens[0].expiration.split('.')[0]
        self.assertEqual(pers_token_expiry_str, exp_expiry_date_str)

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token=self.session_token)
        result = auth_client.destroySession()

        self.assertTrue(result, "Server did not allow us to destroy session.")

        self.session_token = auth_client.performLogin(
            "Username:Password", "colon:my:password")
        self.assertIsNotNone(self.session_token,
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
        self.session_token = auth_token_client.performLogin(
            "Username:Password", "cc:" + token)

        self.assertIsNotNone(self.session_token,
                             "Valid credentials didn't give us a token!")

        auth_token_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.session_token)
        user = auth_token_client.getLoggedInUser()
        self.assertEqual(user, "cc")

        result = auth_token_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Kill the session token that was created by login() too.
        codechecker.logout(self._test_cfg['codechecker_cfg'],
                           self._test_workspace)

        self.session_token = auth_client.performLogin(
            "Username:Password", "cc:test")
        self.assertIsNotNone(self.session_token,
                             "Valid credentials didn't give us a token!")

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token=self.session_token)
        # Remove the generated personal token.
        ret = auth_client.removePersonalAccessToken(name)
        self.assertTrue(ret)

        # Check whether no more personal token in the database.
        personal_tokens = auth_client.getPersonalAccessTokens()
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

    def try_login(self, provider, username, password):
        """
        Emulating login flow of user in CodeChecker.
        """
        auth_client = env.setup_auth_client(
            self._test_workspace, session_token='_PROHIBIT')

        link = auth_client.createLink(provider)
        data = requests.get(
            url=f"{link}&username={username}&password={password}",
            timeout=10).json()

        if 'error' in data:
            raise RequestFailed(data['error'])

        link = link.split('?')[0]

        code, state = data['code'], data['state']

        # CSRF attack case
        if username == "user_csrf":
            state = "FAKESTATE"

        auth_string = f"{link}?code={code}&state={state}"

        # PKCE attack case
        if username == "user_pkce":
            code="wrong_code"
            auth_string = f"{link}?code={code}&state={state}"

        self.session_token = auth_client.performLogin(
            "oauth", provider + "@" + auth_string)

        return {
            "session_token": self.session_token,
            "state": state
        }

    def test_oauth_insert_session(self):
        """
        Testing if correct login flow inserts user's session data in
        oauth_sessions table.
        """
        session_factory = env.create_sqlalchemy_session(self._test_workspace)

        state = self.try_login("github", "admin_github", "admin")\
            .get('state', None)
        result = env.validate_oauth_session(session_factory, state)
        self.assertTrue(result, "OAuth state wasn't inserted in Database")

        state = self.try_login("google", "user_google", "user")\
            .get('state', None)
        result = env.validate_oauth_session(session_factory, state)
        self.assertTrue(result, "OAuth state wasn't inserted in Database")

    def test_oauth_token_session(self):
        """
        Testing if correct login flow inserts
        user's oauth token data into the oauth_tokens table.
        """
        session_factory = env.create_sqlalchemy_session(self._test_workspace)

        session = self.try_login("github", "admin_github", "admin")
        self.assertTrue(session, "Authentication failed")

        result = env.validate_oauth_token_session(session_factory, "github1",)
        self.assertTrue(result, "Access_token wasn't inserted in Database")

        session = self.try_login("google", "user_google", "user")
        self.assertTrue(session, "Authentication failed")

        result = env.validate_oauth_token_session(session_factory, "google3",)
        self.assertTrue(result, "Access_token wasn't inserted in Database")

    def test_oauth_regular_users(self):
        """
        Tests if the regular users can log in with OAuth.
        """
        # The following user is in the list of allowed users: GITHUB
        session_token = self.try_login("github", "admin_github", "admin")\
            .get('session_token', None)
        self.assertIsNotNone(session_token,
                             "Valid credentials didn't give us a token!")

        session_token = self.try_login("google", "user_google", "user")\
            .get('session_token', None)
        self.assertIsNotNone(session_token,
                             "Valid credentials didn't give us a token!")

    def test_oauth_create_link(self):
        """
        Tests functionality of create_link method
        that checks if it creates unique links correctly.
        """

        from urllib.parse import urlparse, parse_qs

        auth_client = env.setup_auth_client(
            self._test_workspace, session_token='_PROHIBIT')
        session_factory = env.create_sqlalchemy_session(self._test_workspace)

        # check 1
        link_github = auth_client.createLink("github")
        parsed_query = parse_qs(urlparse(link_github).query)
        state = parsed_query.get("state")[0]
        result = env.validate_oauth_session(session_factory, state)
        self.assertIsNotNone(link_github,
                             "Authorization link for Github created empty")
        self.assertTrue(result, "create link wasn't seccesfully executed")

        # check 2
        link_google = auth_client.createLink("google")
        parsed_query = parse_qs(urlparse(link_google).query)
        state = parsed_query.get("state")[0]
        result = env.validate_oauth_session(session_factory, state)
        self.assertTrue(result, "create link wasn't seccesfully executed")
        self.assertIsNotNone(link_google,
                             "Authorization link for Google created empty")

        self.assertNotEqual(link_github,
                            link_google,
                            "Function created identical links")

    def test_oauth_invalid_credentials(self):
        """
        Testing the oauth using non-existent users.
        """

        with self.assertRaises(RequestFailed):
            self.try_login("google", "non-existant", "test")

        with self.assertRaises(RequestFailed):
            self.try_login("github", "non-existant", "test")

    def test_oauth_csrf_attack_protection(self):
        """
        Tests if authorization server returns a state
        that doesn't exist in database.
        """

        with self.assertRaises(RequestFailed):
            self.try_login("github", "user_csrf", "user")

        with self.assertRaises(RequestFailed):
            self.try_login("google", "user_csrf", "user")

    def test_oauth_pkce_attack_protection(self):
        """
        Tests using pkce user performs attack to validate presence of
        pkce attack protection.
        The user tries to login with a code_verifier that is not in the
        database, so the authentication should fail.
        """

        with self.assertRaises(RequestFailed):
            self.try_login("github", "user_pkce", "user")

        with self.assertRaises(RequestFailed):
            self.try_login("google", "user_pkce", "user")

    def test_oauth_incomplete_token_data(self):
        """
        Tests if in case of returned incomplete tokens data,
        etc.
        missing access_token,
        missing expires_in(access token expiration time),
        missing refresh_token,
        missing token type,
        missing scope,
        """

        with self.assertRaises(RequestFailed):
            self.try_login("github",
                           "user_incomplete_token",
                           "user")

    def test_oauth_remove_old_sessions(self):
        """
        Tests if the old oauth sessions are removed from database
        during the login process.
        Test manually inserts a session with expired time,
        etc(15 minutes ago) and then tries to login with valid credentials.
        The old session should be removed and the new one should be created.
        """

        session_factory = env.create_sqlalchemy_session(self._test_workspace)

        # user that should be removed
        state_r = "FAKESTATE"
        code_verifier_r = "54GJITG3gVBT"
        provider_r = "github"
        # creates a session that should expire on new login.
        expires_at_r = datetime.now() \
            - timedelta(minutes=32)

        env.insert_oauth_session(session_alchemy=session_factory,
                                 state=state_r,
                                 code_verifier=code_verifier_r,
                                 provider=provider_r,
                                 expires_at=expires_at_r)

        result = env.validate_oauth_session(session_factory, state_r)
        # validate that the session was inserted
        self.assertTrue(result, "Session that will be removed "
                        "was not inserted")

        # user that should login successfully and remove the old session
        session_token = self.try_login("github", "admin_github", "admin")\
            .get('session_token', None)
        self.assertIsNotNone(session_token,
                             "Valid credentials didn't give us a token!")

        validate_removed = env.validate_oauth_session(session_factory, state_r)
        self.assertFalse(validate_removed, "old oauth session wasn't removed")

    def test_oauth_wrong_callback_url_format(self):
        """
        Tests if 'always_off' provider with wrong callback URL format
        is not in the list of providers.
        In the test server configuration the 'always_off' provider
        is configured with a callback URL that does not match the
        expected format.
        """
        auth_client = env.setup_auth_client(
            self._test_workspace, session_token='_PROHIBIT')

        providers = auth_client.getOauthProviders()
        self.assertNotIn("always_off", providers, "'always_off' provider "
                         "should not be in the list of providers."
                         "Callback_URL checker is not working properly.")

    def test_oauth_callback_url_valid(self):
        """
        Tests a valid case of callback URL format.
        The callback URL should be in the format:
        <host>/login/OAuthLogin/<provider>
        """
        # Check a correct callback URL format.
        valid_callback_url = "https://example.com/login/OAuthLogin/github"
        self.assertTrue(SessMgr.check_callback_url_format("github",
                                                          valid_callback_url),
                        "Valid callback URL was rejected.")

    def test_oauth_callback_url_format_checker(self):
        """
        Tests if the callback URL format checker correctly
        rejects invalid callback URLs.
        The callback URL should be in the format:
        <host>/login/OAuthLogin/<provider>
        """

        valid_callback_url = "https://example.com/login/OAuthLogin/banana"
        self.assertFalse(
            SessMgr.check_callback_url_format("github", valid_callback_url),
            "Invalid callback URL was accepted.")

        invalid_callback_url = "https://example.com/login/OAuthLogin/github/"
        self.assertFalse(
            SessMgr.check_callback_url_format("github", invalid_callback_url),
            "Invalid callback URL was accepted.")

        invalid_callback_url = "https://examputhLogin/github/"
        self.assertFalse(
            SessMgr.check_callback_url_format("github", invalid_callback_url),
            "Invalid callback URL was accepted.")

        invalid_callback_url = \
            "https://example.com/login/OAuthLogin/github/extra"
        self.assertFalse(
            SessMgr.check_callback_url_format("github", invalid_callback_url),
            "Invalid callback URL was accepted.")

        invalid_callback_url = "https://example.com/OAuthLogin/github"
        self.assertFalse(
            SessMgr.check_callback_url_format("github", invalid_callback_url),
            "Invalid callback URL was accepted.")

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
        self.session_token = auth_client.performLogin(
            "Username:Password", "root:root")

        self.assertIsNotNone(self.session_token,
                             "Valid credentials didn't give us a token!")

        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.session_token)
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
        self.session_token = \
            auth_client.performLogin("Username:Password",
                                     "admin_group_user:admin123")

        self.assertIsNotNone(self.session_token,
                             "Valid credentials didn't give us a token!")

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=self.session_token)

        self.assertIsNotNone(client.allowsStoringAnalysisStatistics(),
                             "Privileged server didn't respond properly.")

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

    def test_regex_groups(self):
        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')
        # First login as root.
        self.session_token = auth_client.performLogin(
            "Username:Password", "root:root")
        self.assertIsNotNone(self.session_token,
                             "root was unable to login!")

        # Then give SUPERUSER privs to admins_custom_group.
        authd_auth_client = \
            env.setup_auth_client(self._test_workspace,
                                  session_token=self.session_token)
        ret = authd_auth_client.addPermission(Permission.SUPERUSER,
                                              "admins_custom_group",
                                              True, None)
        self.assertTrue(ret)

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Login as a user who is in admins_custom_group.
        session_token = auth_client.performLogin(
            "Username:Password", "regex_admin:blah")
        self.assertIsNotNone(session_token,
                             "Valid credentials didn't give us a token!")

        # Do something privileged.
        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=session_token)
        self.assertIsNotNone(client.allowsStoringAnalysisStatistics(),
                             "Privileged call failed.")

        result = auth_client.destroySession()
        self.assertTrue(result, "Server did not allow us to destroy session.")

        # Finally try to do the same with an unprivileged user.
        session_token = auth_client.performLogin(
            "Username:Password", "john:doe")
        self.assertIsNotNone(session_token,
                             "Valid credentials didn't give us a token!")

        client = env.setup_viewer_client(self._test_workspace,
                                         session_token=session_token)
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
                         '--url', env.parts_to_url(codechecker_cfg),
                         '--expiration', '10',
                         'my_token']

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
                         tokens[0]['name']]

        subprocess.check_output(
            del_token_cmd,
            encoding="utf-8",
            errors="ignore")

        cred_manager.save_token(host, port, session_token, True)

    def test_config_failed_auth_message_showing_in_cli(self):
        """
        Test if the failed_auth_message from the server config shows up in
        cli upon failed authentication.
        """

        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')

        with self.assertRaises(RequestFailed) as msg:
            auth_client.performLogin("Username:Password", "invalid:invalid")

        self.assertIn("Note: Personal access token based authentication only",
                      str(msg.exception))

    def test_announcement_showing_in_cli(self):
        """
        Test if the announcement message posted on the CodeChecker GUI shows
        up in cli.
        """
        # Authenticate (SU permission required)
        auth_client = env.setup_auth_client(self._test_workspace,
                                            session_token='_PROHIBIT')
        session_token = auth_client.performLogin(
            "Username:Password", "root:root")

        auth_client.addPermission(Permission.SUPERUSER, "root", False, "")

        # Set announcement message
        su_config_client = env.setup_config_client(self._test_workspace,
                                                   session_token=session_token)

        su_config_client.setNotificationBannerText(
            convert.to_b64('Test announcement msg!'))

        # Check if the message shows up
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            codechecker.login(self._test_cfg['codechecker_cfg'],
                              self._test_workspace,
                              'root',
                              'root')
        output = f.getvalue()

        self.assertIn("Announcement: Test announcement msg!", output)
