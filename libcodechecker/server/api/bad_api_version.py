# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for authentication.
"""

import shared

from libcodechecker.logger import get_logger
from libcodechecker.profiler import timeit

LOG = get_logger('system')


class ThriftAPIMismatchHandler(object):
    """
    Handle Thrift authentication requests.
    """

    def __init__(self, used_version):
        self.__request_version = used_version

    @timeit
    def checkAPIVersion(self):
        raise shared.ttypes.RequestFailed(
            shared.ttypes.ErrorCode.API_MISMATCH,
            "The API version you tried to connect to ({0}) is not "
            "supported by this server.".format(self.__request_version))
