# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Thrift client setup and configuration.
"""


import getpass
import sys

from thrift.Thrift import TApplicationException

import codechecker_api_shared
from codechecker_api.Authentication_v6 import ttypes as AuthTypes

from codechecker_common.logger import get_logger

from codechecker_web.shared import env
from codechecker_web.shared.version import CLIENT_API

from codechecker_client.helpers.authentication import ThriftAuthHelper
from codechecker_client.helpers.product import ThriftProductHelper
from codechecker_client.helpers.results import ThriftResultsHelper
from .credential_manager import UserCredentials
from .product import split_product_url

LOG = get_logger('system')


def check_preconfigured_username(username, host, port):
    """
    Checks if username supplied by using preconfigured credentials.
    """
    if not username:
        LOG.error("No username supplied! Please specify the "
                  "username in your \"%s\" file for %s:%d.",
                  env.get_password_file(), host, port)
        sys.exit(1)


def init_auth_client(protocol, host, port):
    """ Setup a new auth client. """
    auth_client = setup_auth_client(protocol, host, port)

    # Check if local token is available.
    cred_manager = UserCredentials()
    session_token = cred_manager.get_token(host, port)

    if not session_token:
        LOG.info("No valid token or session was found for %s:%s", host, port)
        session_token = perform_auth_for_handler(auth_client, host, port,
                                                 cred_manager)

    return setup_auth_client(protocol, host, port, session_token)


def setup_auth_client(protocol, host, port, session_token=None):
    """
    Setup the Thrift authentication client. Returns the client object and the
    session token for the session.
    """
    client = ThriftAuthHelper(protocol, host, port,
                              '/v' + CLIENT_API + '/Authentication',
                              session_token)

    return client


def login_user(protocol, host, port, username, login=False):
    """ Login with the given user name.

    If login is False the user will be logged out.
    """
    session = UserCredentials()
    auth_client = ThriftAuthHelper(protocol, host, port,
                                   '/v' + CLIENT_API + '/Authentication')

    if not login:
        logout_done = auth_client.destroySession()
        if logout_done:
            session.save_token(host, port, None, True)
            LOG.info("Successfully logged out.")
        return

    try:
        handshake = auth_client.getAuthParameters()

        if not handshake.requiresAuthentication:
            LOG.info("This server does not require privileged access.")
            return

    except TApplicationException:
        LOG.info("This server does not support privileged access.")
        return

    methods = auth_client.getAcceptedAuthMethods()
    # Attempt username-password auth first.
    if 'Username:Password' in str(methods):

        # Try to use a previously saved credential from configuration file if
        # autologin is enabled.
        saved_auth = None
        if session.is_autologin_enabled():
            saved_auth = session.get_auth_string(host, port)

        if saved_auth:
            LOG.info("Logging in using preconfigured credentials...")
            username = saved_auth.split(":")[0]
            pwd = saved_auth.split(":")[1]
            check_preconfigured_username(username, host, port)
        else:
            LOG.info("Logging in using credentials from command line...")
            pwd = getpass.getpass(
                "Please provide password for user '{}': ".format(username))

        LOG.debug("Trying to login as %s to %s:%d", username, host, port)
        try:
            session_token = auth_client.performLogin("Username:Password",
                                                     username + ":" +
                                                     pwd)

            session.save_token(host, port, session_token)
            LOG.info("Server reported successful authentication.")
        except codechecker_api_shared.ttypes.RequestFailed as reqfail:
            LOG.error("Authentication failed! Please check your credentials.")
            LOG.error(reqfail.message)
            sys.exit(1)
    else:
        LOG.critical("No authentication methods were reported by the server "
                     "that this client could support.")
        sys.exit(1)


def perform_auth_for_handler(auth_client, host, port, manager):
    # Before actually communicating with the server,
    # we need to check authentication first.

    try:
        auth_response = auth_client.getAuthParameters()
    except TApplicationException:
        auth_response = AuthTypes.HandshakeInformation()
        auth_response.requiresAuthentication = False

    if auth_response.requiresAuthentication and \
            not auth_response.sessionStillActive:

        if manager.is_autologin_enabled():
            auto_auth_string = manager.get_auth_string(host, port)
            if auto_auth_string:
                LOG.info("Logging in using pre-configured credentials...")

                username = auto_auth_string.split(':')[0]
                check_preconfigured_username(username, host, port)

                LOG.debug("Trying to login as '%s' to '%s:%d'", username,
                          host, port)

                # Try to automatically log in with a saved credential
                # if it exists for the server.
                try:
                    session_token = auth_client.performLogin(
                        "Username:Password",
                        auto_auth_string)
                    manager.save_token(host, port, session_token)
                    LOG.info("Authentication successful.")
                    return session_token
                except codechecker_api_shared.ttypes.RequestFailed:
                    pass

        if manager.is_autologin_enabled():
            LOG.error("Invalid pre-configured credentials.")
            LOG.error("Your password has been changed or personal access "
                      "token has been removed which is used by your "
                      "\"%s\" file. Please "
                      "remove or change invalid credentials.",
                      env.get_password_file())
        else:
            LOG.error("Access denied. This server requires "
                      "authentication.")
            LOG.error("Please log in onto the server using 'CodeChecker "
                      "cmd login'.")
        sys.exit(1)


def setup_product_client(protocol, host, port, auth_client=None,
                         product_name=None,
                         session_token=None):
    """Setup the Thrift client for the product management endpoint."""
    cred_manager = UserCredentials()
    session_token = cred_manager.get_token(host, port)

    if not session_token:
        auth_client = setup_auth_client(protocol, host, port)
        session_token = perform_auth_for_handler(auth_client, host, port,
                                                 cred_manager)

    if not product_name:
        # Attach to the server-wide product service.
        product_client = ThriftProductHelper(
            protocol, host, port,
            '/v' + CLIENT_API + '/Products',
            session_token,
            lambda: get_new_token(protocol, host, port, cred_manager))
    else:
        # Attach to the product service and provide a product name
        # as "viewpoint" from which the product service is called.
        product_client = ThriftProductHelper(
            protocol, host, port,
            '/' + product_name + '/v' + CLIENT_API + '/Products',
            session_token,
            lambda: get_new_token(protocol, host, port, cred_manager))

        # However, in this case, the specified product might not exist,
        # which means we can't communicate with the server orderly.
        if not product_client.getPackageVersion() or \
                not product_client.getCurrentProduct():
            LOG.error("The product '%s' cannot be communicated with. It "
                      "either doesn't exist, or the server's configuration "
                      "is bogus.", product_name)
            sys.exit(1)

    return product_client


def get_new_token(protocol, host, port, cred_manager):
    """ Get a new session token from the remote server. """
    auth_client = setup_auth_client(protocol, host, port)
    return perform_auth_for_handler(auth_client, host, port, cred_manager)


def setup_client(product_url) -> ThriftResultsHelper:
    """Setup the Thrift Product or Service client and
    check API version and authentication needs.
    """

    try:
        protocol, host, port, product_name = split_product_url(product_url)
    except ValueError:
        LOG.error("Malformed product URL was provided. A valid product URL "
                  "looks like this: 'http://my.server.com:80/ProductName'.")
        sys.exit(2)  # 2 for argument error.

    # Check if local token is available.
    cred_manager = UserCredentials()
    session_token = cred_manager.get_token(host, port)

    # Local token is missing ask remote server.
    if not session_token:
        session_token = get_new_token(protocol, host, port, cred_manager)

    LOG.debug("Initializing client connecting to %s:%d/%s done.",
              host, port, product_name)

    return ThriftResultsHelper(
        protocol, host, port,
        '/' + product_name + '/v' + CLIENT_API + '/CodeCheckerService',
        session_token,
        lambda: get_new_token(protocol, host, port, cred_manager))
