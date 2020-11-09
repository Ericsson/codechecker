# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper for the configuration thrift api.
"""

from codechecker_api.Configuration_v6 import configurationService

from codechecker_client.thrift_call import ThriftClientCall
from .base import BaseClientHelper


class ThriftConfigHelper(BaseClientHelper):
    def __init__(self, protocol, host, port, uri, session_token=None):
        super().__init__(protocol, host, port, uri, session_token)

        self.client = configurationService.Client(self.protocol)

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getNotificationBannerText(self):
        pass
