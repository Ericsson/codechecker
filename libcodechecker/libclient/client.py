# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import getpass
import sys

from thrift.Thrift import TApplicationException

import shared
from Authentication import ttypes as AuthTypes

from libcodechecker import session_manager
from libcodechecker.logger import LoggerFactory

from . import thrift_helper
from . import authentication_helper

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
        else:
            LOG.info("Server requires authentication to access. Please use "
                     "'CodeChecker cmd login' to authenticate.")

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


def setup_client(host, port, uri):
    """
    Stup the thrift client and check API version and authentication needs.
    """
    manager = session_manager.SessionManager_Client()
    session_token = manager.getToken(host, port)

    # Before actually communicating with the server,
    # we need to check authentication first.
    auth_client = authentication_helper.ThriftAuthHelper(host,
                                                         port,
                                                         uri +
                                                         'Authentication',
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

    client = thrift_helper.ThriftClientHelper(host, port, uri, session_token)
    # Test if client can work with the server's API.
    if not check_api_version(client):
        LOG.critical("The server uses a newer version of the API which is "
                     "incompatible with this client. Please update client.")
        sys.exit(1)

    return client
