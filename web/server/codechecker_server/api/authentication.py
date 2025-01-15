# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests for authentication.
"""

import datetime
import sqlite3

from authlib.integrations.requests_client import OAuth2Session
from authlib.common.security import generate_token
from urllib.parse import urlparse, parse_qs

import json
import codechecker_api_shared

from collections import defaultdict

from codechecker_api.Authentication_v6.ttypes import AccessControl, \
    AuthorisationList, HandshakeInformation, Permissions, SessionTokenData

from codechecker_common.logger import get_logger

from codechecker_server.profiler import timeit

from ..database.config_db_model import Product, ProductPermission, Session, \
    OAuthSession, SystemPermission
from ..database.database import DBSession
from ..permissions import handler_from_scope_params as make_handler, \
    require_manager, require_permission
from ..server import permissions
from ..session_manager import generate_session_token


LOG = get_logger('server')


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftAuthHandler:
    """
    Handle Thrift authentication requests.
    """

    def __init__(self, manager, auth_session, config_database):
        self.__manager = manager
        self.__auth_session = auth_session
        self.__config_db = config_database

    def __require_privilaged_access(self):
        """
        Checks if privilaged access is enabled for the server. Throws an
        exception if it is not.
        """
        if not self.getLoggedInUser():
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                "The server must be start by using privilaged access to "
                "execute this action.")

    def __has_permission(self, permission) -> bool:
        """ True if the current user has given permission rights. """
        if self.__manager.is_enabled and not self.__auth_session:
            return False

        return self.hasPermission(permission, None)

    def __require_permission_view(self):
        """
        Checks if the curret user has PERMISSION_VIEW rights. Throws an
        exception if it is not.
        """
        permission = codechecker_api_shared.ttypes.Permission.PERMISSION_VIEW
        if not self.__has_permission(permission):
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                "You are not authorized to execute this action.")

    @timeit
    def checkAPIVersion(self):
        # This is a deliberate empty call which if succeeds, marks for the
        # client that the server accepted the connection proper.
        pass

    # ============= Authentication and session handling =============

    @timeit
    def getAuthParameters(self):
        alive = self.__auth_session.is_alive if self.__auth_session \
                else False
        return HandshakeInformation(self.__manager.is_enabled, alive)

    @timeit
    def getLoggedInUser(self):
        return self.__auth_session.user if self.__auth_session else ""

    @timeit
    def getAcceptedAuthMethods(self):
        return ["Username:Password", "oauth"]

    @timeit
    def getAccessControl(self):
        self.__require_permission_view()

        with DBSession(self.__config_db) as session:
            global_permissions = Permissions(
                user=defaultdict(list),
                group=defaultdict(list))

            q = session.query(SystemPermission).all()
            for system_permission in q:
                name = system_permission.name
                perm = system_permission.permission
                if system_permission.is_group:
                    global_permissions.group[name].append(perm)
                else:
                    global_permissions.user[name].append(perm)

            product_permissions = {}
            q = session \
                .query(Product.endpoint, ProductPermission) \
                .outerjoin(Product,
                           ProductPermission.product_id == Product.id) \
                .all()

            for endpoint, product_permission in q:
                if endpoint not in product_permissions:
                    product_permissions[endpoint] = Permissions(
                        user=defaultdict(list),
                        group=defaultdict(list))

                name = product_permission.name
                perm = product_permission.permission
                if product_permission.is_group:
                    product_permissions[endpoint].group[name].append(perm)
                else:
                    product_permissions[endpoint].user[name].append(perm)

        default_superuser = self.__manager.default_superuser_name
        if default_superuser:
            global_permissions.user[default_superuser].append("SUPERUSER")

        return AccessControl(
            globalPermissions=global_permissions,
            productPermissions=product_permissions)

    @timeit
    def insertDataOauth(self, state, code_verifier, provider):
        """
        Insert the state code and verification code into the database
        """

        # remove all the expired state codes from the database
        try:
            date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with DBSession(self.__config_db) as session:
                session.execute("DELETE FROM oauth_sessions "
                                "WHERE expires_at "
                                "< DATETIME(\"" + date + "\")")
                session.commit()
            LOG.info("Expired state, validation codes removed successfully.")
        except sqlite3.Error as e:
            LOG.error(f"An error occurred: {e}")

        # Insert the state code into the database
        try:
            with DBSession(self.__config_db) as session:
                LOG.debug(f"State {state} insertion started.")
                date = (datetime.datetime.now() +
                        datetime.timedelta(minutes=15))

                new_state = OAuthSession(state=state,
                                         code_verifier=code_verifier,
                                         expires_at=date,
                                         provider=provider)
                session.add(new_state)
                session.commit()

                LOG.info("State inserted successfully.")

        except sqlite3.Error as e:
            LOG.error(f"An error occurred: {e}")
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                "OAuth data insertion failed. Please try again.")

    @timeit
    def getOauthProviders(self):
        return self.__manager.get_oauth_providers()

    @timeit
    def createLink(self, provider):
        """
        For creating a autehntication link for OAuth for specified provider
        """
        oauth_config = self.__manager.get_oauth_config(provider)
        if not oauth_config.get('enabled'):
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                "OAuth authentication is not enabled.")

        stored_state = generate_token()
        client_id = oauth_config["oauth_client_id"]
        client_secret = oauth_config["oauth_client_secret"]
        scope = oauth_config["oauth_scope"]
        authorization_uri = oauth_config["oauth_authorization_uri"]
        callback_url = oauth_config["oauth_callback_url"]
        # code verifier for PKCE
        pkce_verifier = generate_token(48)

        # Create an OAuth2Session instance
        session = OAuth2Session(
            client_id,
            client_secret,
            scope=scope,
            redirect_uri=callback_url,
            code_challenge_method='S256'
            )

        # each provider has different requirements
        # for requesting refresh token
        if provider == "google":
            url, state = session.create_authorization_url(
                url=authorization_uri,
                state=stored_state,
                code_verifier=pkce_verifier,
                access_type='offline',
                prompt='consent'
            )
        else:
            url, state = session.create_authorization_url(
                authorization_uri,
                state=stored_state,
                code_verifier=pkce_verifier
            )
        # inserting data in database
        self.insertDataOauth(state=state,
                             code_verifier=pkce_verifier,
                             provider=provider)

        return url

    @timeit
    def performLogin(self, auth_method, auth_string):
        if not auth_string:
            raise codechecker_api_shared.ttypes.RequestFailed(
                codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                "No credentials supplied. Refusing authentication!")

        if auth_method == "Username:Password":
            user_name, _ = auth_string.split(':', 1)
            LOG.debug("'%s' logging in...", user_name)

            session = self.__manager.create_session(auth_string)

            if session:
                LOG.info("'%s' logged in.", user_name)
                return session.token
            else:
                msg = f"Invalid credentials supplied for user " \
                    f"'{user_name}'. Refusing authentication!"

                LOG.warning(msg)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    msg)

        elif auth_method == "oauth":
            date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            provider, url = auth_string.split("@")
            # make the provider not case sensitive
            provider = provider.lower()
            url_new = urlparse(url)
            parsed_query = parse_qs(url_new.query)
            code = parsed_query.get("code")[0]
            state = parsed_query.get("state")[0]
            code_verifier_db = None
            state_db = None
            provider_db = None
            expires_at = None

            with DBSession(self.__config_db) as session:
                state_db, code_verifier_db, provider_db, expires_at = \
                    session.query(OAuthSession.state,
                                  OAuthSession.code_verifier,
                                  OAuthSession.provider,
                                  OAuthSession.expires_at) \
                           .filter(OAuthSession.state == state) \
                           .first()

            # make the provider from the database not case sensitive
            provider_db = provider_db.lower()

            if str(state_db) != state or str(provider_db) != provider \
                    or str(date_time) > str(expires_at):
                LOG.error("State code mismatch.")
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "Something went wrong. Please try again.")

            oauth_config = self.__manager.get_oauth_config(provider)
            if not oauth_config.get('enabled'):
                LOG.error("OAuth authentication is " +
                          "not enabled for provider: %s", provider)
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "OAuth authentication is not enabled.")

            client_id = oauth_config["oauth_client_id"]
            client_secret = oauth_config["oauth_client_secret"]
            scope = oauth_config["oauth_scope"]
            authorization_uri = oauth_config["oauth_authorization_uri"]
            token_url = oauth_config["oauth_token_uri"]
            user_info_url = oauth_config["oauth_user_info_uri"]
            callback_url = oauth_config["oauth_callback_url"]
            allowed_users = oauth_config.get("allowed_users", [])
            LOG.info("OAuth configuration loaded for provider: %s", provider)
            session = None
            try:
                session = OAuth2Session(
                    client_id,
                    client_secret,
                    scope=scope,
                    redirect_uri=callback_url,
                    code_challenge_method='S256'
                    )

            except Exception as ex:
                LOG.error("OAuth2Session creation failed: %s", str(ex))
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "OAuth2Session creation failed.")

            # recreating the url for pkce purpose
            # no way to get the original session so recreate it

            url_recreated = session.create_authorization_url(
                authorization_uri,
                state=state_db,
                code_verifier=code_verifier_db
                )[0]

            hashed_challenge = urlparse(url_recreated)
            parsed_query_r = parse_qs(hashed_challenge.query)
            cc = parsed_query_r.get("code_challenge")[0]

            # FIXME: This is a workaround for the Microsoft OAuth2 provider
            # which doesn't correctly fetch the code from url.
            # the workaround is to construct the url manually

            url = url_new.scheme + "://" + url_new.netloc + url_new.path + \
                "?code=" + code + "&state=" + state + \
                "&code_challenge=" + cc + \
                "&code_challenge_method=S256"

            LOG.info("URL has been constructed successfully")
            token = None
            try:
                # code_verifier_db or PKCE is't supported by github
                # if it will be fixed the code should adjust automatically
                token = session.fetch_token(
                    url=token_url,
                    authorization_response=url,
                    code_verifier=code_verifier_db)
            except Exception as ex:
                LOG.error("Token fetch failed: %s", str(ex))
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "Token fetch failed.")
            LOG.info("Token fetched successfully for provider: %s", provider)

            user_info = None
            username = None

            try:
                user_info = session.get(user_info_url).json()
                username = user_info[
                    oauth_config["oauth_user_info_mapping"]["username"]]
                LOG.info("User info fetched, username: %s", username)
            except Exception as ex:
                LOG.error("User info fetch failed: %s", str(ex))
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "User info fetch failed.")

            # if the provider is github it fetches primary email
            # from another api endpoint to maintain username as email
            # consistency between GitHub and other providers
            if provider == "github" and \
                    "localhost" not in user_info_url:
                try:
                    link = "https://api.github.com/user/emails"
                    for email in session.get(link).json():
                        if email['primary']:
                            username = email['email']
                            LOG.info("Primary email found: %s", username)
                            break
                except Exception as ex:
                    LOG.error("Email fetch failed: %s", str(ex))
                    raise codechecker_api_shared.ttypes.RequestFailed(
                        codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                        "Email fetch failed.")

            if allowed_users == ["*"] or username in allowed_users:
                LOG.info("User %s is authorized.", username)
                session = self.__manager.create_session_oauth(
                    provider, username, token['access_token'])
                return session.token

            if len(allowed_users) == 0:
                LOG.error("The allowed users list is empty.")
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "User is not authorized to access this service")

            LOG.error("User %s is not authorized " +
                      "to access this service.", username)
            raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
                    "User is not authorized to access this service")
        LOG.error("Could not negotiate via common authentication method.")
        raise codechecker_api_shared.ttypes.RequestFailed(
            codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED,
            "Could not negotiate via common authentication method.")

    @timeit
    def destroySession(self):
        user_name = self.getLoggedInUser()
        LOG.debug("'%s' logging out...", user_name)

        token = None
        if self.__auth_session:
            token = self.__auth_session.token

        is_logged_out = self.__manager.invalidate(token)
        if is_logged_out:
            LOG.info("'%s' logged out.", user_name)
        return is_logged_out

    # ============= Authorization, permission management =============

    @staticmethod
    def __unpack_extra_params(extra_params, session=None):
        """
        Helper function to unpack the extra_params JSON string to a dict.

        If specified, add the config_db_session to this dict too.
        """

        if extra_params and extra_params != "":
            params = json.loads(extra_params)
        else:
            params = {}

        if session:
            params['config_db_session'] = session

        return params

    @staticmethod
    def __create_permission_args(perm_enum, extra_params_string, session):
        """
        Helper function to transform the permission-specific values from the
        API into the appropriate Python constructs needed by the permission
        library.
        """

        perm = permissions.permission_from_api_enum(perm_enum)
        params = ThriftAuthHandler.__unpack_extra_params(extra_params_string,
                                                         session)
        return perm, params

    @timeit
    def getPermissions(self, scope):
        """
        Returns all the defined permissions in the given permission scope.
        """

        return [permissions.api_enum_for_permission(p)
                for p in permissions.get_permissions(scope)]

    @timeit
    def getPermissionsForUser(self, scope, extra_params, perm_filter):
        """
        Returns the permissions in the given permission scope and with the
        given scope-specific extra_params for the current logged in user,
        based on the permission filters.

        Filters in the perm_filter struct are joined in an AND clause.
        """

        if perm_filter is None or not any(perm_filter.__dict__.values()):
            # If no filtering is needed, this function behaves identically
            # to getPermissions().
            return self.getPermissions(scope)

        with DBSession(self.__config_db) as session:
            # The database connection must always be passed to the permission
            # handler.
            params = ThriftAuthHandler.__unpack_extra_params(extra_params,
                                                             session)

            perms = []
            for perm in permissions.get_permissions(scope):
                should_return = True
                handler = make_handler(perm, params)

                if should_return and perm_filter.given:
                    should_return = handler.has_permission(self.__auth_session)

                if should_return and perm_filter.canManage:
                    # If the user has any of the permissions that are
                    # authorised to manage the currently iterated permission,
                    # the filter passes.
                    should_return = require_manager(
                         perm, params, self.__auth_session)

                if should_return:
                    perms.append(perm)

            return [permissions.api_enum_for_permission(p)
                    for p in perms]

    @timeit
    def getAuthorisedNames(self, permission, extra_params):
        """
        Returns the users and groups who were EXPLICITLY granted a particular
        permission.
        """

        with DBSession(self.__config_db) as session:
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            if not require_manager(perm, params, self.__auth_session):
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                    f"You can not manage the permission '{perm.name}'")

            handler = make_handler(perm, params)
            users, groups = handler.list_permitted()

            # The special default permission marker is an internal value.
            users = [user for user in users if user != '*']

            return AuthorisationList(users, groups)

    @timeit
    def addPermission(self, permission, auth_name, is_group, extra_params):
        """
        Adds the given permission to the user or group named auth_name.
        """

        with DBSession(self.__config_db) as session:
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            if not require_manager(perm, params, self.__auth_session):
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                    f"You can not manage the permission '{perm.name}'")

            handler = make_handler(perm, params)
            handler.add_permission(auth_name.strip(),
                                   is_group,
                                   user_name=self.getLoggedInUser())

            session.commit()
            return True

    @timeit
    def removePermission(self, permission, auth_name, is_group, extra_params):
        """
        Removes the given permission from the user or group auth_name.
        """

        with DBSession(self.__config_db) as session:
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            if not require_manager(perm, params, self.__auth_session):
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED,
                    f"You can not manage the permission '{perm.name}'")

            handler = make_handler(perm, params)
            handler.remove_permission(auth_name, is_group,
                                      user_name=self.getLoggedInUser())

            session.commit()
            return True

    @timeit
    def hasPermission(self, permission, extra_params):
        """
        Returns whether or not the current logged-in user (or guest, if
        authentication is disabled) is granted the given permission.

        This method observes permission inheritance.
        """

        with DBSession(self.__config_db) as session:
            perm, params = ThriftAuthHandler.__create_permission_args(
                permission, extra_params, session)

            return require_permission(perm, params,
                                      self.__auth_session)

    # ============= Authorization, permission management =============

    @timeit
    def newToken(self, description):
        """
        Generate a new personal access token with the given description.
        """
        self.__require_privilaged_access()
        with DBSession(self.__config_db) as session:
            token = generate_session_token()
            user = self.getLoggedInUser()
            groups = ';'.join(self.__auth_session.groups)
            session_token = Session(token, user, groups, description, False)

            session.add(session_token)
            session.commit()

            LOG.info("New personal access token '%s...' has been generated "
                     "by '%s'.", token[:5], self.getLoggedInUser())

            return SessionTokenData(token,
                                    description,
                                    str(session_token.last_access))

    @timeit
    def removeToken(self, token):
        """
        Removes the given personal access token of the logged in user.
        """
        self.__require_privilaged_access()
        with DBSession(self.__config_db) as session:
            # Check if the given token is a personal access token so it can be
            # removed.
            user = self.getLoggedInUser()
            num_of_removed = session.query(Session) \
                .filter(Session.user_name == user) \
                .filter(Session.token == token) \
                .filter(Session.can_expire.is_(False)) \
                .delete(synchronize_session=False)
            session.commit()

            if not num_of_removed:
                raise codechecker_api_shared.ttypes.RequestFailed(
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE,
                    f"Personal access token {token} was not found in the "
                    "database.")

            # Invalidate the local session by token.
            self.__manager.invalidate_local_session(token)

            LOG.info("Personal access token '%s...' has been removed by '%s'.",
                     token[:5], self.getLoggedInUser())

            return True

    @timeit
    def getTokens(self):
        """
        Get available personal access tokens of the logged in user.
        """
        self.__require_privilaged_access()
        with DBSession(self.__config_db) as session:
            user = self.getLoggedInUser()
            sessionTokens = session.query(Session) \
                .filter(Session.user_name == user) \
                .filter(Session.can_expire.is_(False)) \
                .all()

            result = []
            for t in sessionTokens:
                result.append(SessionTokenData(
                    t.token,
                    t.description,
                    str(t.last_access)))

            return result
