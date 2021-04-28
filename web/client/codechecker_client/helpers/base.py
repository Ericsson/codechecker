# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Base Helper class for Thrift api calls.
"""

import sys
from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol

from codechecker_client.credential_manager import SESSION_COOKIE_NAME
from codechecker_client.product import create_product_url

from codechecker_common.logger import get_logger

LOG = get_logger('system')


class BaseClientHelper:

    def __init__(self, protocol, host, port, uri, session_token=None,
                 get_new_token=None):
        """
        @param get_new_token: a function which can generate a new token.
        """
        self.__host = host
        self.__port = port
        url = create_product_url(protocol, host, port, uri)

        self.transport = None

        try:
            self.transport = THttpClient.THttpClient(url)
        except ValueError:
            # Initalizing THttpClient may raise an exception if proxy settings
            # are used but the port number is not a valid integer.
            pass

        # Thrift do not handle the use case when invalid proxy format is
        # used (e.g.: no schema is specified). For this reason we need to
        # verify the proxy format in our side.
        self._validate_proxy_format()

        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = None

        self.get_new_token = get_new_token
        self._set_token(session_token)

    def _validate_proxy_format(self):
        """
        Validate the proxy settings.
        If the proxy settings are invalid, it will print an error message and
        stop the program.
        """
        if self.transport and not self.transport.using_proxy():
            return

        if not self.transport or not self.transport.host or \
                not isinstance(self.transport.port, int):
            LOG.error("Invalid proxy format! Check your "
                      "HTTP_PROXY/HTTPS_PROXY environment variables if "
                      "these are in the right format: "
                      "'http[s]://host:port'.")
            sys.exit(1)

    def _set_token(self, session_token):
        """ Set the given token in the transport layer. """
        if not session_token:
            return

        headers = {'Cookie': SESSION_COOKIE_NAME + '=' + session_token}
        self.transport.setCustomHeaders(headers)

    def _reset_token(self):
        """ Get a new token and update the transport layer. """
        if not self.get_new_token:
            return

        # get_new_token() function connects to a remote server to get a new
        # session token.
        session_token = self.get_new_token()
        self._set_token(session_token)
