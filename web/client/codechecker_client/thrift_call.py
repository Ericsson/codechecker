# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper for thrift api calls.
"""


import sys

from thrift.protocol.TProtocol import TProtocolException
from thrift.Thrift import TApplicationException

import codechecker_api_shared

from codechecker_common.logger import get_logger

LOG = get_logger('system')


def truncate_arg(arg, max_len=100):
    """ Truncate the given argument if the length is too large. """
    if isinstance(arg, str) and len(arg) > max_len:
        return arg[:max_len] + "..."

    return arg


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
            try:
                return func(*args, **kwargs)
            except TApplicationException as ex:
                # If the session is expired we will try to reset the token and
                # call the API function again.
                if "Error code 401" not in ex.message:
                    raise ex

                # Generate a new token
                self._reset_token()

                return func(*args, **kwargs)
        except codechecker_api_shared.ttypes.RequestFailed as reqfailure:
            LOG.error('Calling API endpoint: %s', funcName)
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
                LOG.error('Ask the product admin for additional access '
                          'rights.')
            elif reqfailure.errorCode ==\
                    codechecker_api_shared.ttypes.ErrorCode.API_MISMATCH:
                LOG.error('Client/server API mismatch\n %s',
                          str(reqfailure.message))
            else:
                LOG.error('API call error: %s\n%s', funcName, str(reqfailure))
            sys.exit(1)
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

            # Do not print the argument list if it contains sensitive
            # information such as passwords.
            # Also it is possible that one of the argument is too large to log
            # the full content of it (for example the 'b64zip' parameter of the
            # 'massStoreRun' API function). For this reason we have to truncate
            # the arguments.
            if funcName != "performLogin":
                LOG.error([truncate_arg(arg) for arg in args])

            LOG.error(kwargs)
            LOG.exception("Request failed.")
            sys.exit(1)
        except OSError as oserr:
            LOG.error("Connection failed.")
            LOG.error(oserr.strerror)
            LOG.error("Check if your CodeChecker server is running.")
            sys.exit(1)
        finally:
            self.transport.close()

    return wrapper
