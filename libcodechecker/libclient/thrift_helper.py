# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from thrift.transport import THttpClient
from thrift.protocol import TJSONProtocol

from codeCheckerDBAccess_v6 import codeCheckerDBAccess

from libcodechecker import util
from libcodechecker.libclient.thrift_call import ThriftClientCall
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

    @ThriftClientCall
    def getRunData(self, run_name_filter):
        pass

    @ThriftClientCall
    def getRunHistory(self, run_ids, limit, offset, run_history_filter):
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

    # SOURCE COMPONENT RELATED API CALLS

    @ThriftClientCall
    def addSourceComponent(self, name, value, description):
        pass

    @ThriftClientCall
    def getSourceComponents(self, component_filter):
        pass

    @ThriftClientCall
    def removeSourceComponent(self, name):
        pass

    # STORAGE RELATED API CALLS

    @ThriftClientCall
    def getMissingContentHashes(self, file_hashes):
        pass

    @ThriftClientCall
    def massStoreRun(self, name, tag, version, zipdir, force,
                     trim_path_prefixes):
        pass
