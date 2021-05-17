# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handle Thrift requests for server info.
"""

from codechecker_common.logger import get_logger
from codechecker_server.profiler import timeit

LOG = get_logger('server')


class ThriftServerInfoHandler:
    """
    Manages Thrift requests regarding server info.
    """

    def __init__(self, package_version):
        self.__package_version = package_version

    @timeit
    def getPackageVersion(self):
        """ Get package version. """
        return self.__package_version
