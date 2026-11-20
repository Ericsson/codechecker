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
if caching is turned on. The API calls use the standard client helpers
(automatic re-authentication if the session token expires). The helpers
call sys.exit() on errors: the callers in the analysis workers handle it as
a cache miss. The ERROR messages of the cache API calls are logged with
WARNING level, because a failing cache access does not fail the analysis.
"""

import json
import logging
from contextlib import contextmanager

from codechecker_api.python.AnalysisCache_v6.ttypes import CacheContent
from codechecker_api.python.shared.ttypes import Permission

from codechecker_common.logger import get_logger

from codechecker_web.shared.webserver_context import get_context

from .client import get_new_token, setup_auth_client, setup_product_client
from .credential_manager import USER_CREDENTIALS
from .helpers.analysis_cache import ThriftAnalysisCacheHelper
from .product import split_product_url

LOG = get_logger('system')


class _ErrorToWarningFilter(logging.Filter):
    """ Log the ERROR (and more severe) records with WARNING level. """

    def filter(self, record):
        if record.levelno >= logging.ERROR:
            record.levelno = logging.WARNING
            record.levelname = logging.getLevelName(logging.WARNING)
        return True


@contextmanager
def _errors_as_warnings():
    """
    Log the ERROR messages of the client helpers (thrift_call,
    re-authentication) with WARNING level while the block runs.
    """
    log_filter = _ErrorToWarningFilter()
    LOG.addFilter(log_filter)
    try:
        yield
    finally:
        LOG.removeFilter(log_filter)


def is_server_reachable(protocol, host, port, timeout=30) -> bool:
    """
    Returns False (and logs the reason with WARNING level) if the
    CodeChecker server can not be connected.
    """
    auth_client = setup_auth_client(protocol, host, port)
    auth_client.transport.setTimeout(int(timeout * 1000))
    try:
        with _errors_as_warnings():
            auth_client.getAuthParameters()
    except SystemExit:
        return False
    return True


def authenticate(url: str):
    """
    Authenticate to the server of the given product URL. This must be called
    in the main process: it can prompt for credentials and it calls
    sys.exit() on authentication failure.

    The session token is stored in USER_CREDENTIALS, the subsequent API
    calls take it from there. Returns (protocol, host, port, product).
    """
    protocol, host, port, product = split_product_url(url)

    if not USER_CREDENTIALS.get_token(host, port):
        get_new_token(protocol, host, port, USER_CREDENTIALS)

    return protocol, host, port, product


def check_product(protocol, host, port, product) -> int:
    """
    Check that the product exists on the server and return its ID. Calls
    sys.exit() with an error message if the product can not be communicated
    with.
    """
    product_client = setup_product_client(protocol, host, port,
                                          product_name=product)
    return product_client.getCurrentProduct().id


def has_cache_permission(protocol, host, port, product_id: int) -> bool:
    """
    Returns whether the user has the PRODUCT_CACHE permission on the
    product. Calls sys.exit() with an error message if the API call fails.
    """
    # Called right after the authentication in the main process, so the
    # session token is fresh (ThriftAuthHelper does not renew tokens).
    auth_client = setup_auth_client(protocol, host, port,
                                    USER_CREDENTIALS.get_token(host, port))
    return auth_client.hasPermission(Permission.PRODUCT_CACHE,
                                     json.dumps({'productID': product_id}))


class AnalysisCacheClient:
    """ Client of the AnalysisCache API of a product. """

    def __init__(self, protocol, host, port, product,
                 connect_timeout=5, read_timeout=30):
        api = get_context().api_version
        self.__helper = ThriftAnalysisCacheHelper(
            protocol, host, port, f"/{product}/v{api}/AnalysisCache",
            USER_CREDENTIALS.get_token(host, port),
            lambda: get_new_token(protocol, host, port, USER_CREDENTIALS),
            timeout=max(connect_timeout, read_timeout))

    def read_cache(self, key: str) -> list[tuple[str, str]]:
        """ Returns the (filename, encoded content) pairs of the entry. """
        with _errors_as_warnings():
            contents = self.__helper.readCache(key) or []
        return [(c.filename, c.content) for c in contents]

    def write_cache(self, key: str, contents: list[tuple[str, str]]):
        with _errors_as_warnings():
            self.__helper.writeCache(
                key, [CacheContent(filename=name, content=content)
                      for name, content in contents])
