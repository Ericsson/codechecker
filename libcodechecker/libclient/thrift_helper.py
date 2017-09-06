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
                if reqfailure.errorCode == shared.ttypes.ErrorCode.DATABASE:
                    print('Database error on server')
                    print(str(reqfailure.message))
                elif reqfailure.errorCode ==\
                        shared.ttypes.ErrorCode.AUTH_DENIED:
                    print('Authentication denied')
                    print(str(reqfailure.message))
                elif reqfailure.errorCode ==\
                        shared.ttypes.ErrorCode.UNAUTHORIZED:
                    print('Unauthorized to access')
                    print(str(reqfailure.message))
                else:
                    print('API call error: ' + funcName)
                    print(str(reqfailure))

                raise

            except TProtocolException as ex:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
                print("Check if your CodeChecker server is running.")
                sys.exit(1)
            except socket.error as serr:
                print("Connection failed to {0}:{1}"
                      .format(self.__host, self.__port))
                errCause = os.strerror(serr.errno)
                print(errCause)
                print(str(serr))
                print("Check if your CodeChecker server is running.")
                sys.exit(1)
            finally:
                self.transport.close()

        return wrapper

    @ThriftClientCall
    def getRunData(self, runNameFilter):
        pass

    @ThriftClientCall
    def getRunResults(self, runIds, limit, offset, sortType, reportFilters):
        pass

    @ThriftClientCall
    def getSourceFileData(self, fileId, fileContent, encoding):
        pass

    @ThriftClientCall
    def getRunResultCount(self, runIds, reportFilters):
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

    @ThriftClientCall
    def changeReviewStatus(self, report_id, status, message):
        pass

    @ThriftClientCall
    def changeReviewStatusByHash(self, bug_hash, status, message):
        pass

    @ThriftClientCall
    def getRunResults_v2(self, runIds, limit, offset, sortType, reportFilter,
                         cmpData):
        pass

    @ThriftClientCall
    def getRunResultCount_v2(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getSeverityCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getCheckerMsgCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getReviewStatusCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getDetectionStatusCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getFileCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getCheckerCounts(self, base_run_ids, reportFilter, cmpData):
        pass

    # STORAGE RELATED API CALLS

    @ThriftClientCall
    def getMissingContentHashes(self, file_hashes):
        pass

    @ThriftClientCall
    def massStoreRun(self, name, version, zipdir, force):
        pass

    @ThriftClientCall
    def replaceConfigInfo(self, run_id, values):
        pass
