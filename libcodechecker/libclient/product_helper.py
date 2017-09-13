# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
# import datetime
import socket

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException

import shared
from ProductManagement_v6 import codeCheckerProductService

from libcodechecker import session_manager
from libcodechecker import util


class ThriftProductHelper(object):
    def __init__(self, protocol, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        url = util.create_product_url(protocol, host, port, uri)
        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerProductService.Client(self.protocol)

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
                return res
            except shared.ttypes.RequestFailed as reqfailure:
                if reqfailure.errorCode == shared.ttypes.ErrorCode.DATABASE:
                    print('Database error on server')
                    print(str(reqfailure.message))
                elif reqfailure.errorCode ==\
                        shared.ttypes.ErrorCode.AUTH_DENIED:
                    print('Authentication denied.')
                    raise reqfailure
                elif reqfailure.errorCode ==\
                        shared.ttypes.ErrorCode.UNAUTHORIZED:
                    print('Unauthorised.')
                    raise reqfailure
                else:
                    print('Other error')
                    print(str(reqfailure))
            except TProtocolException as ex:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
            except socket.error as serr:
                errCause = os.strerror(serr.errno)
                print(errCause)
                print(str(serr))
            finally:
                # after = datetime.datetime.now()
                # timediff = after - before
                # diff = timediff.microseconds/1000
                # print('['+str(diff)+'ms] <<<<< ['+host+':'+str(port)+']')
                # print res
                self.transport.close()

        return wrapper

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getPackageVersion(self):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getProducts(self, product_endpoint_filter, product_name_filter):
        pass

    @ThriftClientCall
    def getCurrentProduct(self):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def addProduct(self, product):
        pass

    @ThriftClientCall
    def removeProduct(self, product_id):
        pass
