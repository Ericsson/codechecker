# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Helper for the product thrift api.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol

from ProductManagement_v6 import codeCheckerProductService

from libcodechecker import util
from libcodechecker.logger import get_logger

from .thrift_call import ThriftClientCall
from .credential_manager import SESSION_COOKIE_NAME

LOG = get_logger('system')


class ThriftProductHelper(object):
    def __init__(self, protocol, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        url = util.create_product_url(protocol, host, port, uri)
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
