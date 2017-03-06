# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys
# import datetime
import socket

from thrift import Thrift
from thrift.Thrift import TException, TApplicationException
from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException

import shared
from Authentication import codeCheckerAuthentication

from libcodechecker import session_manager


class ThriftAuthHelper():
    def __init__(self, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        self.transport = THttpClient.THttpClient(self.__host, self.__port, uri)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerAuthentication.Client(self.protocol)

        if session_token:
            headers = {'Cookie': session_manager.SESSION_COOKIE_NAME +
                       "=" + session_token}
            self.transport.setCustomHeaders(headers)

            # ------------------------------------------------------------

    def ThriftClientCall(function):
        # print type(function)
        funcName = function.__name__

        def wrapper(self, *args, **kwargs):
            # print('['+host+':'+str(port)+'] >>>>> ['+funcName+']')
            # before = datetime.datetime.now()
            self.transport.open()
            func = getattr(self.client, funcName)
            try:
                res = func(*args, **kwargs)

            except shared.ttypes.RequestFailed as reqfailure:
                if reqfailure.error_code == shared.ttypes.ErrorCode.DATABASE:
                    print('Database error on server')
                    print(str(reqfailure.message))
                if reqfailure.error_code == shared.ttypes.ErrorCode.PRIVILEGE:
                    raise reqfailure
                else:
                    print('Other error')
                    print(str(reqfailure))

                sys.exit(1)
            except TProtocolException as ex:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
                sys.exit(1)
            except socket.error as serr:
                errCause = os.strerror(serr.errno)
                print(errCause)
                print(str(serr))
                sys.exit(1)

            # after = datetime.datetime.now()
            # timediff = after - before
            # diff = timediff.microseconds/1000
            # print('['+str(diff)+'ms] <<<<< ['+host+':'+str(port)+']')
            # print res
            self.transport.close()
            return res

        return wrapper

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getAuthParameters(self):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getAcceptedAuthMethods(self):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def performLogin(self, auth_method, auth_string):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def destroySession(self):
        pass
