# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper for the "analysis cache" Thrift API.
"""
from typing import Callable

from codechecker_api.python.AnalysisCache_v6 import AnalysisCache
from codechecker_api.python.AnalysisCache_v6.ttypes import CacheContent

from ..thrift_call import thrift_client_call
from .base import BaseClientHelper


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftAnalysisCacheHelper(BaseClientHelper):
    """Clientside Thrift stub for the `AnalysisCache` service."""

    def __init__(self, protocol: str, host: str, port: int, uri: str,
                 session_token: str | None = None,
                 get_new_token: Callable | None = None,
                 timeout: float | None = None):
        super().__init__(protocol, host, port, uri,
                         session_token, get_new_token)

        if timeout:
            # THttpClient has a single timeout (ms) for connect and read.
            self.transport.setTimeout(int(timeout * 1000))

        self.client = AnalysisCache.Client(self.protocol)

    @thrift_client_call
    def writeCache(self, _key: str, _contents: list[CacheContent]):
        raise NotImplementedError("Should have called Thrift code!")

    @thrift_client_call
    def readCache(self, _key: str) -> list[CacheContent]:
        raise NotImplementedError("Should have called Thrift code!")
