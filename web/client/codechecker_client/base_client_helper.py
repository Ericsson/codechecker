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


from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol

from .credential_manager import SESSION_COOKIE_NAME
from .product import create_product_url


class BaseClientHelper(object):

    def __init__(self, protocol, host, port, uri, session_token=None,
                 get_new_token=None):
        """
        @param get_new_token: a function which can generate a new token.
        """
        self.__host = host
        self.__port = port
        url = create_product_url(protocol, host, port, uri)

        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = None

        self.get_new_token = get_new_token
        self._set_token(session_token)

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
