# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
import os
import socket
import sys

from thrift.protocol.TProtocol import TProtocolException
from thrift.Thrift import TApplicationException

import shared
from libcodechecker.logger import get_logger

LOG = get_logger('system')


def ThriftClientCall(function):
    """ Wrapper function for thrift client calls.
        - open and close transport,
        - log and handle errors
    """
    # LOG.debug(type(function))
    funcName = function.__name__

    def wrapper(self, *args, **kwargs):
        # LOG.debug('['+self.__host+':'+str(self.__port)+'] '
        #       '>>>>> ['+funcName+']')
        # before = datetime.datetime.now()
        self.transport.open()
        func = getattr(self.client, funcName)
        try:
            res = func(*args, **kwargs)
            return res
        except shared.ttypes.RequestFailed as reqfailure:
            if reqfailure.errorCode == shared.ttypes.ErrorCode.DATABASE:
                LOG.error('Database error on server')
                LOG.error(str(reqfailure.message))
            elif reqfailure.errorCode ==\
                    shared.ttypes.ErrorCode.AUTH_DENIED:
                LOG.error('Authentication denied')
                LOG.error(str(reqfailure.message))
            elif reqfailure.errorCode ==\
                    shared.ttypes.ErrorCode.UNAUTHORIZED:
                LOG.error('Unauthorized to access')
                LOG.error(str(reqfailure.message))
            elif reqfailure.errorCode ==\
                    shared.ttypes.ErrorCode.API_MISMATCH:
                LOG.error('Client/server API mismatch')
                LOG.error(str(reqfailure.message))
            else:
                LOG.error('API call error: ' + funcName)
                LOG.error(str(reqfailure))

            raise
        except TApplicationException as ex:
            LOG.error("Internal server error on {0}:{1}"
                      .format(self.__host, self.__port))
            LOG.error(ex.message)
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
            LOG.error(ex.message)
            LOG.error("Request failed to {0}:{1}"
                      .format(self.__host, self.__port))
            sys.exit(1)
        except socket.error as serr:
            LOG.error("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
            errCause = os.strerror(serr.errno)
            LOG.error(errCause)
            LOG.error(str(serr))
            LOG.error("Check if your CodeChecker server is running.")
            sys.exit(1)
        finally:
            self.transport.close()

    return wrapper
