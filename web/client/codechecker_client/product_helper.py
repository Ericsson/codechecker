# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper for the product thrift api.
"""


from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol

from codechecker_api.ProductManagement_v6 import codeCheckerProductService

from codechecker_common.logger import get_logger

from .credential_manager import SESSION_COOKIE_NAME
from .product import create_product_url
from .thrift_call import ThriftClientCall

LOG = get_logger('system')


class ThriftProductHelper(object):
    def __init__(self, protocol, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        url = create_product_url(protocol, host, port, uri)
        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerProductService.Client(self.protocol)

        if session_token:
            headers = {'Cookie': SESSION_COOKIE_NAME + '=' + session_token}
            self.transport.setCustomHeaders(headers)

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getPackageVersion(self):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getProducts(self, product_endpoint_filter, product_name_filter):
        pass

    @ThriftClientCall
    def getCurrentProduct(self):
        pass

    @ThriftClientCall
    def getProductConfiguration(self, product_id):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def addProduct(self, product):
        pass

    @ThriftClientCall
    def removeProduct(self, product_id):
        pass
