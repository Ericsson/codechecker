# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Helper for the configuration thrift api.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol

from Configuration_v6 import configurationService

from codechecker_common.logger import get_logger

from .credential_manager import SESSION_COOKIE_NAME
from .product import create_product_url
from .thrift_call import ThriftClientCall

LOG = get_logger('system')


class ThriftConfigHelper(object):
    def __init__(self, protocol, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        url = create_product_url(protocol, host, port, uri)
        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = configurationService.Client(self.protocol)

        if session_token:
            headers = {'Cookie': SESSION_COOKIE_NAME + '=' + session_token}
            self.transport.setCustomHeaders(headers)

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getNotificationBannerText(self):
        pass
