# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Helper functions for Thrift api calls.
"""

from codechecker_api.codeCheckerDBAccess_v6 import codeCheckerDBAccess

from codechecker_client.thrift_call import ThriftClientCall
from .base import BaseClientHelper


class ThriftResultsHelper(BaseClientHelper):

    def __init__(self, protocol, host, port, uri, session_token=None,
                 get_new_token=None):
        """
        @param get_new_token: a function which can generate a new token.
        """
        super().__init__(protocol, host, port, uri, session_token,
                         get_new_token)

        self.client = codeCheckerDBAccess.Client(self.protocol)

    @ThriftClientCall
    def getRunData(self, run_name_filter, limit, offset, sort_mode):
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
    def getDiffResultsHash(self, run_ids, report_hashes, diff_type,
                           skip_detection_statuses, tag_ids):
        pass

    @ThriftClientCall
    def getRunResultTypes(self, runId, reportFilters):
        pass

    @ThriftClientCall
    def removeRunResults(self, run_ids):
        pass

    @ThriftClientCall
    def removeRunReports(self, run_ids, report_filter, cmp_data):
        pass

    @ThriftClientCall
    def removeRun(self, run_id, run_filter):
        pass

    @ThriftClientCall
    def updateRunData(self, run_id, new_run_name):
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
    def getReviewStatusRules(self, filter, sortMode, limit, offset):
        pass

    @ThriftClientCall
    def getRunResults(self, runIds, limit, offset, sortType, reportFilter,
                      cmpData, getDetails):
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

    @ThriftClientCall
    def exportData(self, runId):
        pass

    @ThriftClientCall
    def importData(self, exportData):
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
    def getMissingContentHashesForBlameInfo(self, file_hashes):
        pass

    @ThriftClientCall
    def massStoreRun(self, name, tag, version, zipdir, force,
                     trim_path_prefixes, description):
        pass

    @ThriftClientCall
    def allowsStoringAnalysisStatistics(self):
        pass

    @ThriftClientCall
    def getAnalysisStatisticsLimits(self):
        pass

    @ThriftClientCall
    def getAnalysisStatistics(self, run_id, run_history_id):
        pass

    @ThriftClientCall
    def storeAnalysisStatistics(self, run_name, zip_file):
        pass
