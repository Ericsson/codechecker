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

from codechecker_api.ProductManagement_v6 import codeCheckerProductService

from codechecker_client.thrift_call import ThriftClientCall
from .base import BaseClientHelper


class ThriftProductHelper(BaseClientHelper):
    def __init__(self, protocol, host, port, uri, session_token=None,
                 get_new_token=None):
        """
        @param get_new_token: a function which can generate a new token.
        """
        super().__init__(protocol, host, port, uri, session_token,
                         get_new_token)

        self.client = codeCheckerProductService.Client(self.protocol)

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
