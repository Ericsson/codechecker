# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Helper for thrift api calls.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import socket
import sys

from thrift.protocol.TProtocol import TProtocolException
from thrift.Thrift import TApplicationException

import codechecker_api_shared

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def ThriftClientCall(function):
    """ Wrapper function for thrift client calls.
        - open and close transport,
        - log and handle errors
    """
    funcName = function.__name__

    def wrapper(self, *args, **kwargs):
        self.transport.open()
        func = getattr(self.client, funcName)
        try:
            res = func(*args, **kwargs)
            return res
        except codechecker_api_shared.ttypes.RequestFailed as reqfailure:
            if reqfailure.errorCode ==\
                    codechecker_api_shared.ttypes.ErrorCode.DATABASE:
                LOG.error('Database error on server\n%s',
                          str(reqfailure.message))
            elif reqfailure.errorCode ==\
                    codechecker_api_shared.ttypes.ErrorCode.AUTH_DENIED:
                LOG.error('Authentication denied\n %s',
                          str(reqfailure.message))
            elif reqfailure.errorCode ==\
                    codechecker_api_shared.ttypes.ErrorCode.UNAUTHORIZED:
                LOG.error('Unauthorized to access\n %s',
                          str(reqfailure.message))
            elif reqfailure.errorCode ==\
                    codechecker_api_shared.ttypes.ErrorCode.API_MISMATCH:
                LOG.error('Client/server API mismatch\n %s',
                          str(reqfailure.message))
            else:
                LOG.error('API call error: %s\n%s', funcName, str(reqfailure))

            raise
        except TApplicationException as ex:
            LOG.error("Internal server error: %s", str(ex.message))
            sys.exit(1)
        except TProtocolException as ex:
            if ex.type == TProtocolException.UNKNOWN:
                LOG.error('Unknown thrift error')
            elif ex.type == TProtocolException.INVALID_DATA:
                LOG.error('Thrift invalid data error.')
            elif ex.type == TProtocolException.NEGATIVE_SIZE:
                LOG.error('Thrift negative size error.')
            elif ex.type == TProtocolException.SIZE_LIMIT:
                LOG.error('Thrift size limit error.')
            elif ex.type == TProtocolException.BAD_VERSION:
                LOG.error('Thrift bad version error.')
            LOG.error(funcName)
            LOG.error(args)
            LOG.error(kwargs)
            LOG.exception("Request failed.")
            sys.exit(1)
        except socket.error as serr:
            LOG.error("Connection failed.")
            errCause = os.strerror(serr.errno)
            LOG.error(errCause)
            LOG.error(str(serr))
            LOG.error("Check if your CodeChecker server is running.")
            sys.exit(1)
        finally:
            self.transport.close()

    return wrapper
