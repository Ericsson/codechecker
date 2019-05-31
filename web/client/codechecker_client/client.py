# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Thrift client setup and configuration.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import getpass
import json
import sys

from thrift.Thrift import TApplicationException

import shared
from Authentication_v6 import ttypes as AuthTypes

from codechecker_common.logger import get_logger

from codechecker_web.shared.version import CLIENT_API

from . import authentication_helper
from . import product_helper
from . import thrift_helper
from .credential_manager import UserCredentials
from .product import split_product_url

LOG = get_logger('system')


def check_preconfigured_username(username, host, port):
    """
    Checks if username supplied by using preconfigured credentials.
    """
    if not username:
        LOG.error("No username supplied! Please specify the "
                  "username in your "
                  "\"~/.codechecker.passwords.json\" file for "
                  "%s:%d.", host, port)
        sys.exit(1)


def setup_auth_client(protocol, host, port, session_token=None):
    """
    Setup the Thrift authentication client. Returns the client object and the
    session token for the session.
    """

    if not session_token:
        manager = UserCredentials()
        session_token = manager.get_token(host, port)
        session_token_new = perform_auth_for_handler(protocol,
                                                     manager, host,
                                                     port,
                                                     session_token)
        if session_token_new:
            session_token = session_token_new

    client = authentication_helper.ThriftAuthHelper(protocol, host, port,
                                                    '/v' + CLIENT_API +
                                                    '/Authentication',
                                                    session_token)

    return client, session_token


def setup_auth_client_from_url(product_url, session_token=None):
    """
    Setup a Thrift authentication client to the server pointed by the given
    product URL.
    """
    try:
        protocol, host, port, _ = split_product_url(product_url)
        return setup_auth_client(protocol, host, port, session_token)
    except ValueError:
        LOG.error("Malformed product URL was provided. A valid product URL "
                  "looks like this: 'http://my.server.com:80/ProductName'.")
        sys.exit(2)  # 2 for argument error.


def handle_auth(protocol, host, port, username, login=False):
    session = UserCredentials()
    auth_token = session.get_token(host, port)
    auth_client = authentication_helper.ThriftAuthHelper(protocol, host,
                                                         port,
                                                         '/v' +
                                                         CLIENT_API +
                                                         '/Authentication',
                                                         auth_token)

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

        if auth_token and handshake.sessionStillActive:
            LOG.info("You are already logged in.")
            return

    except TApplicationException:
        LOG.info("This server does not support privileged access.")
        return

    methods = auth_client.getAcceptedAuthMethods()
    # Attempt username-password auth first.
    if 'Username:Password' in str(methods):

        # Try to use a previously saved credential from configuration file.
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
        except shared.ttypes.RequestFailed as reqfail:
            LOG.error("Authentication failed! Please check your credentials.")
            LOG.error(reqfail.message)
            sys.exit(1)
    else:
        LOG.critical("No authentication methods were reported by the server "
                     "that this client could support.")
        sys.exit(1)


def perform_auth_for_handler(protocol, manager, host, port,
                             session_token):
    # Before actually communicating with the server,
    # we need to check authentication first.
    auth_client = authentication_helper.ThriftAuthHelper(protocol,
                                                         host,
                                                         port,
                                                         '/v' +
                                                         CLIENT_API +
                                                         '/Authentication',
                                                         session_token)

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
                except shared.ttypes.RequestFailed:
                    pass

        if manager.is_autologin_enabled():
            LOG.error("Invalid pre-configured credentials.")
            LOG.error("Your password has been changed or personal access "
                      "token has been removed which is used by your "
                      "\"~/.codechecker.passwords.json\" file. Please "
                      "remove or change invalid credentials.")
        else:
            LOG.error("Access denied. This server requires "
                      "authentication.")
            LOG.error("Please log in onto the server using 'CodeChecker "
                      "cmd login'.")
        sys.exit(1)


def setup_product_client(protocol, host, port, product_name=None,
                         session_token=None):
    """
    Setup the Thrift client for the product management endpoint.
    """

    _, session_token = setup_auth_client(protocol, host, port, session_token)

    if not product_name:
        # Attach to the server-wide product service.
        product_client = product_helper.ThriftProductHelper(
            protocol, host, port, '/v' + CLIENT_API + '/Products',
            session_token)
    else:
        # Attach to the product service and provide a product name
        # as "viewpoint" from which the product service is called.
        product_client = product_helper.ThriftProductHelper(
            protocol, host, port,
            '/' + product_name + '/v' + CLIENT_API + '/Products',
            session_token)

        # However, in this case, the specified product might not exist,
        # which means we can't communicate with the server orderly.
        if not product_client.getPackageVersion() or \
                not product_client.getCurrentProduct():
            LOG.error("The product '%s' cannot be communicated with. It "
                      "either doesn't exist, or the server's configuration "
                      "is bogus.", product_name)
            sys.exit(1)

    return product_client


def setup_client(product_url, product_client=False):
    """
    Setup the Thrift Product or Service client and
    check API version and authentication needs.
    """

    try:
        protocol, host, port, product_name = split_product_url(product_url)
    except ValueError:
        LOG.error("Malformed product URL was provided. A valid product URL "
                  "looks like this: 'http://my.server.com:80/ProductName'.")
        sys.exit(2)  # 2 for argument error.

    _, session_token = setup_auth_client(protocol, host, port)

    # Check if the product exists.
    client = setup_product_client(protocol, host, port, product_name=None,
                                  session_token=session_token)
    product = client.getProducts(product_name, None)
    product_error_str = None
    if not product:
        product_error_str = "It does not exist."
    elif len(product) != 1:
        product_error_str = "Multiple products can be found with the given " \
                            "name."
    else:
        if product[0].endpoint != product_name:
            # Only a "substring" match was found. We explicitly reject it
            # on the command-line!
            product_error_str = "It does not exist."

        elif not product[0].accessible:
            product_error_str = "You do not have access."

        elif product[0].databaseStatus != shared.ttypes.DBStatus.OK:
            product_error_str = "The database has issues, or the connection " \
                                "is badly configured."

    if product_error_str:
        LOG.error("The given product '%s' can not be used! %s", product_name,
                  product_error_str)
        sys.exit(1)

    if product_client:
        LOG.debug("returning product client")
        return client
    else:
        LOG.debug("returning service client")
        # Service client was requested, setup
        # and return it.
        return setup_service_client(protocol,
                                    host,
                                    port,
                                    product_name,
                                    session_token)


def setup_service_client(protocol, host, port, product_name, session_token):

    client = thrift_helper.ThriftClientHelper(
        protocol, host, port,
        '/' + product_name + '/v' + CLIENT_API + '/CodeCheckerService',
        session_token)

    return client


def check_permission(auth_client, permission_enum, extra_params):
    """
    Returns whether or not the current client has the given permission.

    :param auth_client:     The auth_client usually created by
      setup_auth_client() via which the communication with the server will
      take place.
    :param permission_enum: The Thrift API enum value of the permission. Refer
      to the Authentication API on which permissions exist.
    :param extra_params:    The extra arguments based on the required
      permission's scope (refer to the API documentation) as a Python dict.
    :return: boolean
    """

    # Encode the extra_params into a string over the API.
    args_string = json.dumps(extra_params)

    try:
        return auth_client.hasPermission(permission_enum, args_string)
    except Exception as e:
        LOG.exception("Failed to query the permission.")
        return False
