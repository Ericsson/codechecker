# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import socket

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException

import shared
from codeCheckerDBAccess import codeCheckerDBAccess

from libcodechecker import session_manager


class ThriftClientHelper(object):

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

    def ThriftClientCall(function):
        # print type(function)
        funcName = function.__name__

        def wrapper(self, *args, **kwargs):
            # print('['+self.__host+':'+str(self.__port)+'] '
            #       '>>>>> ['+funcName+']')
            # before = datetime.datetime.now()
            self.transport.open()
            func = getattr(self.client, funcName)
            try:
                res = func(*args, **kwargs)
                return res

            except shared.ttypes.RequestFailed as reqfailure:
                if reqfailure.error_code == shared.ttypes.ErrorCode.DATABASE:
                    print('Database error on server')
                    print(str(reqfailure.message))
                if reqfailure.error_code == shared.ttypes.ErrorCode.PRIVILEGE:
                    print('Unauthorized access')
                    print(str(reqfailure.message))
                else:
                    print('API call error: ' + funcName)
                    print(str(reqfailure))

            except TProtocolException as ex:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
                print("Check if your CodeChecker server is running.")
            except socket.error as serr:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
                errCause = os.strerror(serr.errno)
                print(errCause)
                print(str(serr))
                print("Check if your CodeChecker server is running.")

            self.transport.close()

        return wrapper

    @ThriftClientCall
    def getRunData(self, runNameFilter):
        pass

    @ThriftClientCall
    def getRunResults(self, runId, limit, offset, sortType, reportFilters):
        pass

    @ThriftClientCall
    def getSourceFileData(self, fileId, fileContent, encoding):
        pass

    @ThriftClientCall
    def getRunResultCount(self, runId, reportFilters):
        pass

    @ThriftClientCall
    def getRunResultTypes(self, runId, reportFilters):
        pass

    @ThriftClientCall
    def getAPIVersion(self):
        pass

    @ThriftClientCall
    def removeRunResults(self, run_ids):
        pass

    @ThriftClientCall
    def getSuppressedBugs(self, run_id):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def getNewResults(self, base_run_id, new_run_id, limit, offset, sortType,
                      reportFilters):
        pass

    @ThriftClientCall
    def getUnresolvedResults(self, base_run_id, new_run_id, limit, offset,
                             sortType, reportFilters):
        pass

    @ThriftClientCall
    def getResolvedResults(self, base_run_id, new_run_id, limit, offset,
                           sortType, reportFilters):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def suppressBug(self, runIds, reportId, comment):
        pass

    # -----------------------------------------------------------------------
    @ThriftClientCall
    def unSuppressBug(self, runIds, reportId):
        pass

    # STORAGE RELATED API CALLS

    @ThriftClientCall
    def addCheckerRun(self, command, name, version, force):
        pass

    @ThriftClientCall
    def replaceConfigInfo(self, run_id, values):
        pass

    @ThriftClientCall
    def addSuppressBug(self, run_id, bugsToSuppress):
        pass

    @ThriftClientCall
    def cleanSuppressData(self, run_id):
        pass

    @ThriftClientCall
    def addSkipPath(self, run_id, paths):
        pass

    # The next few following functions must be called via the same connection.
    # =============================================================
    @ThriftClientCall
    def addReport(self, run_id, file_id, bug_hash, checker_message, bugpath,
                  events, checker_id, checker_cat, bug_type, severity,
                  suppress):
        pass

    @ThriftClientCall
    def needFileContent(self, filepath, content_hash):
        pass

    @ThriftClientCall
    def addFileContent(self, content_hash, content, encoding):
        pass

    @ThriftClientCall
    def finishCheckerRun(self, run_id):
        pass

    @ThriftClientCall
    def setRunDuration(self, run_id, duration):
        pass

    @ThriftClientCall
    def stopServer(self):
        pass
