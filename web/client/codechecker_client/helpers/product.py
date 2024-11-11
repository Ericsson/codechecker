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

from codechecker_client.thrift_call import thrift_client_call
from .base import BaseClientHelper


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
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
    @thrift_client_call
    def getPackageVersion(self):
        pass

    # -----------------------------------------------------------------------
    @thrift_client_call
    def getProducts(self, product_endpoint_filter, product_name_filter):
        pass

    @thrift_client_call
    def getCurrentProduct(self):
        pass

    @thrift_client_call
    def getProductConfiguration(self, product_id):
        pass

    # -----------------------------------------------------------------------
    @thrift_client_call
    def addProduct(self, product):
        pass

    @thrift_client_call
    def removeProduct(self, product_id):
        pass
