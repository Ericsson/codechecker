# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import getpass
import json
import sys

from thrift.Thrift import TApplicationException

import shared
from Authentication import ttypes as AuthTypes

from libcodechecker import session_manager
from libcodechecker.logger import LoggerFactory
from libcodechecker.util import split_product_url

from . import authentication_helper
from . import thrift_helper
from . import product_helper

LOG = LoggerFactory.get_new_logger('CLIENT')
SUPPORTED_API_VERSION = '6.0'


def check_api_version(client):
    """
    Check if server API is supported by the client.
    """

    version = client.getAPIVersion()
    supp_major_version = SUPPORTED_API_VERSION.split('.')[0]
    api_major_version = version.split('.')[0]

    # There is NO compatibility between major versions.
    return supp_major_version == api_major_version


def setup_auth_client(host, port, session_token=None):
    """
    Setup the Thrift authentication client. Returns the client object and the
    session token for the session.
    """

    if not session_token:
        manager = session_manager.SessionManager_Client()
        session_token = manager.getToken(host, port)
        session_token_new = perform_auth_for_handler(manager, host,
                                                     port, session_token)
        if session_token_new:
            session_token = session_token_new

    client = authentication_helper.ThriftAuthHelper(host, port,
                                                    '/Authentication',
                                                    session_token)

    return client, session_token


def setup_auth_client_from_url(product_url, session_token=None):
    """
    Setup a Thrift authentication client to the server pointed by the given
    product URL.
    """
    try:
        _, host, port, _ = split_product_url(product_url)
        return setup_auth_client(host, port, session_token)
    except:
        LOG.error("Malformed product URL was provided.")
        sys.exit(2)  # 2 for argument error.


def handle_auth(host, port, username, login=False):
    session = session_manager.SessionManager_Client()
    auth_token = session.getToken(host, port)
    auth_client = authentication_helper.ThriftAuthHelper(host,
                                                         port,
                                                         '/Authentication',
                                                         auth_token)

    if not login:
        logout_done = auth_client.destroySession()
        if logout_done:
            session.saveToken(host, port, None, True)
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
        saved_auth = session.getAuthString(host, port)

        if saved_auth:
            LOG.info("Logging in using preconfigured credentials...")
            username = saved_auth.split(":")[0]
            pwd = saved_auth.split(":")[1]
        else:
            LOG.info("Logging in using credentials from command line...")
            pwd = getpass.getpass("Please provide password for user '{0}'"
                                  .format(username))

        LOG.debug("Trying to login as {0} to {1}:{2}"
                  .format(username, host, port))
        try:
            session_token = auth_client.performLogin("Username:Password",
                                                     username + ":" +
                                                     pwd)

            session.saveToken(host, port, session_token)
            LOG.info("Server reported successful authentication.")
        except shared.ttypes.RequestFailed as reqfail:
            LOG.error("Authentication failed! Please check your credentials.")
            LOG.error(reqfail.message)
            sys.exit(1)
    else:
        LOG.critical("No authentication methods were reported by the server "
                     "that this client could support.")
        sys.exit(1)


def perform_auth_for_handler(manager, host, port, session_token):
    # Before actually communicating with the server,
    # we need to check authentication first.
    auth_client = authentication_helper.ThriftAuthHelper(host,
                                                         port,
                                                         '/Authentication',
                                                         session_token)
    try:
        auth_response = auth_client.getAuthParameters()
    except TApplicationException as tex:
        auth_response = AuthTypes.HandshakeInformation()
        auth_response.requiresAuthentication = False

    if auth_response.requiresAuthentication and \
            not auth_response.sessionStillActive:
        print_err = False

        if manager.is_autologin_enabled():
            auto_auth_string = manager.getAuthString(host, port)
            if auto_auth_string:
                # Try to automatically log in with a saved credential
                # if it exists for the server.
                try:
                    session_token = auth_client.performLogin(
                        "Username:Password",
                        auto_auth_string)
                    manager.saveToken(host, port, session_token)
                    LOG.info("Authenticated using pre-configured "
                             "credentials.")
                    return session_token
                except shared.ttypes.RequestFailed:
                    print_err = True
            else:
                print_err = True
        else:
            print_err = True

        if print_err:
            LOG.error("Access denied. This server requires authentication.")
            LOG.error("Please log in onto the server using 'CodeChecker cmd "
                      "login'.")
            sys.exit(1)


def setup_product_client(host, port, product_name=None):
    """
    Setup the Thrift client for the product management endpoint.
    """

    _, session_token = setup_auth_client(host, port)

    if not product_name:
        # Attach to the server-wide product service.
        product_client = product_helper.ThriftProductHelper(
            host, port, "/Products", session_token)
    else:
        # Attach to the product service and provide a product name
        # as "viewpoint" from which the product service is called.
        product_client = product_helper.ThriftProductHelper(
            host, port, "/" + product_name + "/Products", session_token)

        # However, in this case, the specified product might not be existing,
        # which makes subsequent calls to this API crash (server sends
        # HTTP 500 Internal Server Error error page).
        if not product_client.getAPIVersion():
            LOG.error("The product '{0}' cannot be communicated with. It "
                      "either doesn't exist, or the server's configuration "
                      "is bogus.".format(product_name))
            sys.exit(1)

    if not check_api_version(product_client):
        LOG.critical("The server uses a newer version of the API which is "
                     "incompatible with this client. Please update client.")
        sys.exit(1)

    return product_client


def setup_client(product_url):
    """
    Setup the Thrift client and check API version and authentication needs.
    """

    try:
        _, host, port, product_name = split_product_url(product_url)
    except:
        LOG.error("Malformed product URL was provided.")
        sys.exit(2)  # 2 for argument error.

    _, session_token = setup_auth_client(host, port)

    # Check if the product exists.
    product_client = setup_product_client(host, port,
                                          product_name=None)
    product = product_client.getProducts(product_name, None)
    product_error_str = None
    if not (product and len(product) == 1):
        product_error_str = "It does not exist."
    else:
        if product[0].endpoint != product_name:
            # Only a "substring" match was found. We explicitly reject it
            # on the command-line!
            product_error_str = "It does not exist."
        elif not product[0].connected:
            product_error_str = "The database has issues, or the connection " \
                                "is badly configured."
        elif not product[0].accessible:
            product_error_str = "You do not have access."

    if product_error_str:
        LOG.error("The given product '{0}' can not be used! {1}"
                  .format(product_name, product_error_str))
        sys.exit(1)

    client = thrift_helper.ThriftClientHelper(
        host, port, "/" + product_name + "/CodeCheckerService", session_token)

    # Test if client can work with the server's API.
    if not check_api_version(client):
        LOG.critical("The server uses a newer version of the API which is "
                     "incompatible with this client. Please update client.")
        sys.exit(1)

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
        LOG.error("Failed to query the permission.")
        LOG.error(e.message)
        return False
