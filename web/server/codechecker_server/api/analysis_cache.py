# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests of the product specific analysis cache API
(AnalysisCache).
"""

from codechecker_api.python.AnalysisCache_v6.ttypes import CacheContent
from codechecker_api.python.shared.ttypes import RequestFailed, ErrorCode

from codechecker_common.logger import get_logger

from codechecker_server.profiler import timeit

from .. import permissions
from ..analysis_cache import bazel_remote, cache_store
from ..database.database import DBSession

LOG = get_logger('server')


# pylint: disable=invalid-name
class ThriftAnalysisCacheHandler:
    """
    Thrift handler of the AnalysisCache API of a product.
    """

    def __init__(self, session_manager, auth_session, config_database,
                 product):
        if not product:
            raise ValueError("Cannot initialize the analysis cache handler "
                             "without a product.")

        self.__manager = session_manager
        self.__auth_session = auth_session
        self.__config_database = config_database
        self.__product = product

    def __require_cache_permission(self):
        """
        Raise an UNAUTHORIZED exception if the user does not have the
        PRODUCT_CACHE permission on the product.
        """
        with DBSession(self.__config_database) as session:
            args = {'productID': self.__product.id,
                    'config_db_session': session}
            if not permissions.require_permission(
                    permissions.PRODUCT_CACHE, args, self.__auth_session,
                    self.__manager.is_enabled):
                raise RequestFailed(
                    ErrorCode.UNAUTHORIZED,
                    "You are not authorized to access the analysis cache "
                    "of this product (PRODUCT_CACHE permission is "
                    "required).")

    def __backend(self):
        """
        Returns the cache configuration and the backend client.
        """
        try:
            config = cache_store.CacheConfig.from_dict(
                self.__manager.get_analysis_cache_config())
            client = bazel_remote.get_client(
                config.url, config.user, config.password_file,
                config.timeout)
        except cache_store.CacheNotConfiguredError as ex:
            raise RequestFailed(ErrorCode.GENERAL, str(ex)) from ex
        except bazel_remote.BazelRemoteError as ex:
            LOG.error("Analysis cache: %s", ex)
            raise RequestFailed(ErrorCode.IOERROR,
                                "The analysis cache backend is not "
                                "available.") from ex
        return config, client

    @timeit
    def writeCache(self, key, contents):
        self.__require_cache_permission()
        config, client = self.__backend()

        try:
            cache_store.write_entry(client, self.__product.endpoint, key,
                                    contents, config)
        except cache_store.CacheValidationError as ex:
            raise RequestFailed(ErrorCode.GENERAL, str(ex)) from ex
        except bazel_remote.BazelRemoteError as ex:
            LOG.error("Analysis cache write failed: %s", ex)
            raise RequestFailed(ErrorCode.IOERROR,
                                "Failed to write the analysis cache "
                                "backend.") from ex

    @timeit
    def readCache(self, key):
        self.__require_cache_permission()
        config, client = self.__backend()

        try:
            files = cache_store.read_entry(client, self.__product.endpoint,
                                           key, config)
        except cache_store.CacheValidationError as ex:
            raise RequestFailed(ErrorCode.GENERAL, str(ex)) from ex
        except bazel_remote.BazelRemoteError as ex:
            LOG.error("Analysis cache read failed: %s", ex)
            raise RequestFailed(ErrorCode.IOERROR,
                                "Failed to read the analysis cache "
                                "backend.") from ex

        return [CacheContent(filename=name, content=content)
                for name, content in files]
