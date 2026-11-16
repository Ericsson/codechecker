# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Thrift client of the server-side analysis cache (AnalysisCache API).

This module is imported lazily by codechecker_analyzer.analysis_cache, only
if caching is turned on. Unlike the other client helpers, the API calls never
call sys.exit(): every error is raised to the caller, which handles it as a
cache miss.
"""

from thrift.protocol import TJSONProtocol
from thrift.transport import THttpClient

from codechecker_api.python.AnalysisCache_v6 import AnalysisCache
from codechecker_api.python.AnalysisCache_v6.ttypes import CacheContent

from codechecker_common.logger import get_logger

from codechecker_web.shared.webserver_context import get_context

from .client import get_new_token
from .credential_manager import UserCredentials
from .product import create_product_url, split_product_url

LOG = get_logger('system')


def authenticate(url: str):
    """
    Authenticate to the server of the given product URL. This must be called
    in the main process: it can prompt for credentials and it calls
    sys.exit() on authentication failure.

    Returns (protocol, host, port, product, session_token). The session token
    is None if the server does not require authentication.
    """
    protocol, host, port, product = split_product_url(url)

    cred_manager = UserCredentials()
    token = cred_manager.get_token(host, port)
    if not token:
        token = get_new_token(protocol, host, port, cred_manager)

    return protocol, host, port, product, token


class AnalysisCacheClient:
    """ Client of the AnalysisCache API of a product. """

    def __init__(self, protocol, host, port, product, session_token,
                 connect_timeout=5, read_timeout=30):
        api = get_context().api_version
        url = create_product_url(protocol, host, port,
                                 f"/{product}/v{api}/AnalysisCache")
        self.__transport = THttpClient.THttpClient(url)
        # THttpClient has a single timeout (ms) for connect and read.
        self.__transport.setTimeout(
            int(max(connect_timeout, read_timeout) * 1000))
        if session_token:
            self.__transport.setCustomHeaders(
                {'Authorization': 'Bearer ' + session_token})
        protocol_obj = TJSONProtocol.TJSONProtocol(self.__transport)
        self.__client = AnalysisCache.Client(protocol_obj)

    def read_cache(self, key: str) -> list[tuple[str, str]]:
        """ Returns the (filename, encoded content) pairs of the entry. """
        self.__transport.open()
        try:
            contents = self.__client.readCache(key) or []
        finally:
            self.__transport.close()
        return [(c.filename, c.content) for c in contents]

    def write_cache(self, key: str, contents: list[tuple[str, str]]):
        self.__transport.open()
        try:
            self.__client.writeCache(
                key, [CacheContent(filename=name, content=content)
                      for name, content in contents])
        finally:
            self.__transport.close()
