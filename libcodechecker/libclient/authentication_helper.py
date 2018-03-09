# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
# import datetime
import socket
import sys

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException
from thrift.Thrift import TApplicationException

import shared
from Authentication_v6 import codeCheckerAuthentication

from libcodechecker import util
from libcodechecker.logger import get_logger

from credential_manager import SESSION_COOKIE_NAME

LOG = get_logger('system')


class ThriftAuthHelper():
    def __init__(self, protocol, host, port, uri,
                 session_token=None):
        self.__host = host
        self.__port = port
        url = util.create_product_url(protocol, host, port, uri)
        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerAuthentication.Client(self.protocol)

        if session_token:
            headers = {'Cookie': SESSION_COOKIE_NAME + '=' + session_token}
            self.transport.setCustomHeaders(headers)

            # ------------------------------------------------------------

    def ThriftClientCall(function):
        funcName = function.__name__

        def wrapper(self, *args, **kwargs):
            # LOG.debug('['+host+':'+str(port)+'] >>>>> ['+funcName+']')
            # before = datetime.datetime.now()
            self.transport.open()
            func = getattr(self.client, funcName)
            try:
                res = func(*args, **kwargs)

            except shared.ttypes.RequestFailed as reqfailure:
                if reqfailure.errorCode == shared.ttypes.ErrorCode.DATABASE:
                    LOG.error('Database error on server')
                    LOG.error(str(reqfailure.message))
                elif reqfailure.errorCode ==\
                        shared.ttypes.ErrorCode.AUTH_DENIED:
                    LOG.error('Authentication denied.')
                    raise reqfailure
                elif reqfailure.errorCode ==\
                        shared.ttypes.ErrorCode.UNAUTHORIZED:
                    LOG.error('Unauthorised.')
                    raise reqfailure
                elif reqfailure.errorCode == \
                        shared.ttypes.ErrorCode.API_MISMATCH:
                    raise
                else:
                    LOG.error('Other error')
                    LOG.error(str(reqfailure))

                sys.exit(1)
            except TApplicationException as ex:
                LOG.error("Internal server error on {0}:{1}"
                          .format(self.__host, self.__port))
                LOG.error(ex.message)
            except TProtocolException as ex:
                LOG.error("Connection failed to {0}:{1}"
                          .format(self.__host, self.__port))
                import traceback
                traceback.print_exc()
                sys.exit(1)
            except socket.error as serr:
                errCause = os.strerror(serr.errno)
                LOG.error(errCause)
                LOG.error(str(serr))
                sys.exit(1)

            # after = datetime.datetime.now()
            # timediff = after - before
            # diff = timediff.microseconds/1000
            # LOG.error('['+str(diff)+'ms] <<<<< ['+host+':'+str(port)+']')
            # LOG.error(res)
            self.transport.close()
            return res

        return wrapper

    @ThriftClientCall
    def checkAPIVersion(self):
        pass

    # ============= Authentication and session handling =============
    @ThriftClientCall
    def getAuthParameters(self):
        pass

    @ThriftClientCall
    def getAcceptedAuthMethods(self):
        pass

    @ThriftClientCall
    def performLogin(self, auth_method, auth_string):
        pass

    @ThriftClientCall
    def destroySession(self):
        pass

    # ============= Authorization, permission management =============
    @ThriftClientCall
    def getPermissions(self, scope):
        pass

    @ThriftClientCall
    def getPermissionsForUser(self, scope, extra_params, filter):
        pass

    @ThriftClientCall
    def getAuthorisedNames(self, permission, extra_params):
        pass

    @ThriftClientCall
    def addPermission(self, permission, auth_name, is_group, extra_params):
        pass

    @ThriftClientCall
    def removePermission(self, permission, auth_name, is_group, extra_params):
        pass

    @ThriftClientCall
    def hasPermission(self, permission, extra_params):
        pass
