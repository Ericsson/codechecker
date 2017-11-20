# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import socket
import sys

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol
from thrift.protocol.TProtocol import TProtocolException
from thrift.Thrift import TApplicationException

import shared
from codeCheckerDBAccess_v6 import codeCheckerDBAccess

from libcodechecker import util
from libcodechecker.logger import get_logger

from credential_manager import SESSION_COOKIE_NAME

LOG = get_logger('system')


class ThriftClientHelper(object):

    def __init__(self, protocol, host, port, uri, session_token=None):
        self.__host = host
        self.__port = port
        url = util.create_product_url(protocol, host, port, uri)
        self.transport = THttpClient.THttpClient(url)
        self.protocol = TJSONProtocol.TJSONProtocol(self.transport)
        self.client = codeCheckerDBAccess.Client(self.protocol)

        if session_token:
            headers = {'Cookie': SESSION_COOKIE_NAME + '=' + session_token}
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
            except TApplicationException as ex:
                print("Internal server error on {0}:{1}"
                      .format(self.__host, self.__port))
                print(ex.message)
            except TProtocolException as ex:
                if ex.type == TProtocolException.UNKNOWN:
                    LOG.debug('Unknown thrift error')
                elif ex.type == TProtocolException.INVALID_DATA:
                    LOG.debug('Thrift invalid data error.')
                elif ex.type == TProtocolException.NEGATIVE_SIZE:
                    LOG.debug('Thrift negative size error.')
                elif ex.type == TProtocolException.SIZE_LIMIT:
                    LOG.debug('Thrift size limit error.')
                elif ex.type == TProtocolException.BAD_VERSION:
                    LOG.debug('Thrift bad version error.')
                LOG.debug(funcName)
                LOG.debug(args)
                LOG.debug(kwargs)
                LOG.debug(ex.message)
                print("Request failed to {0}:{1}"
                      .format(self.__host, self.__port))
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
    def getRunData(self, run_name_filter):
        pass

    @ThriftClientCall
    def getReportDetails(self, reportId):
        pass

    @ThriftClientCall
    def getSourceFileData(self, fileId, fileContent, encoding):
        pass

    @ThriftClientCall
    def getLinesInSourceFileContents(self, lines_in_files_requested, encoding):
        pass

    @ThriftClientCall
    def getDiffResultsHash(self, run_ids, report_hashes, diff_type):
        pass

    @ThriftClientCall
    def getRunResultTypes(self, runId, reportFilters):
        pass

    @ThriftClientCall
    def removeRunResults(self, run_ids):
        pass

    @ThriftClientCall
    def getSuppressedBugs(self, run_id):
        pass

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
    def getRunResults(self, runIds, limit, offset, sortType, reportFilter,
                      cmpData):
        pass

    @ThriftClientCall
    def getRunResultCount(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getSeverityCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getCheckerMsgCounts(self, runIds, reportFilter, cmpData, limit,
                            offset):
        pass

    @ThriftClientCall
    def getReviewStatusCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getDetectionStatusCounts(self, runIds, reportFilter, cmpData):
        pass

    @ThriftClientCall
    def getFileCounts(self, runIds, reportFilter, cmpData, limit, offset):
        pass

    @ThriftClientCall
    def getCheckerCounts(self, base_run_ids, reportFilter, cmpData, limit,
                         offset):
        pass

    # STORAGE RELATED API CALLS

    @ThriftClientCall
    def getMissingContentHashes(self, file_hashes):
        pass

    @ThriftClientCall
    def massStoreRun(self, name, tag, version, zipdir, force):
        pass
