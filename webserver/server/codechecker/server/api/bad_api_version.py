# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Handle Thrift requests for authentication.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import shared

from libcodechecker.logger import get_logger
from libcodechecker.profiler import timeit
from libcodechecker.version import get_version_str

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
            "The API version you are using is not "
            "supported by this server.\n"
            "Server API versions: {0} ".format(get_version_str()))
