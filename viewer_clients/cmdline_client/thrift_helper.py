# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import socket
import sys

from thrift import Thrift
from thrift.Thrift import TException, TApplicationException
from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException

from codechecker_lib import session_manager

from codeCheckerDBAccess import codeCheckerDBAccess
import shared


class ThriftClientHelper():

    def __init__(self, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        self.transport = THttpClient.THttpClient(self.__host, self.__port, uri)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerDBAccess.Client(self.protocol)

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
                    print('Unauthorized access')
                    print(str(reqfailure.message))
                else:
                    print('Other error')
                    print(str(reqfailure))

                sys.exit(1)
            except TProtocolException:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
                sys.exit(1)
            except socket.error as serr:
                errCause = os.strerror(serr.errno)
                print(errCause)
                print(str(serr))
                sys.exit(1)

            self.transport.close()
            return res

        return wrapper

    # ------------------------------------------------------------
    @ThriftClientCall
    def getRunData(self):
        pass

    # ------------------------------------------------------------
    @ThriftClientCall
    def getRunResults(self, runId, limit, offset, sortType, reportFilters):
        pass

    # ------------------------------------------------------------
    @ThriftClientCall
    def getRunResultCount(self, runId, reportFilters):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getRunResultTypes(self, runId, reportFilters):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getAPIVersion(self):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def removeRunResults(self, run_ids):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getNewResults(self, base_run_id, new_run_id, limit, offset, sortType,
                      reportFilters):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getUnresolvedResults(self, base_run_id, new_run_id, limit, offset,
                             sortType, reportFilters):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getResolvedResults(self, base_run_id, new_run_id, limit, offset,
                           sortType, reportFilters):
        pass
