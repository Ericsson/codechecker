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

from codechecker_api.codeCheckerDBAccess_v6 import codeCheckerDBAccess, ttypes

from codechecker_client.thrift_call import thrift_client_call
from .base import BaseClientHelper


# These names are inherited from Thrift stubs.
# pylint: disable=invalid-name
class ThriftResultsHelper(BaseClientHelper):

    def __init__(self, protocol, host, port, uri, session_token=None,
                 get_new_token=None):
        """
        @param get_new_token: a function which can generate a new token.
        """
        super().__init__(protocol, host, port, uri, session_token,
                         get_new_token)

        self.client = codeCheckerDBAccess.Client(self.protocol)

    @thrift_client_call
    def getRunData(self, run_name_filter, limit, offset, sort_mode):
        pass

    @thrift_client_call
    def storeFilterPreset(self, preset):
        pass

    @thrift_client_call
    def getFilterPreset(self, id):
        pass

    @thrift_client_call
    def deleteFilterPreset(self, id):
        pass

    @thrift_client_call
    def listFilterPreset(self):
        pass

    @thrift_client_call
    def getRunHistory(self, run_ids, limit, offset, run_history_filter):
        pass

    @thrift_client_call
    def getReportDetails(self, reportId):
        pass

    @thrift_client_call
    def getSourceFileData(self, fileId, fileContent, encoding):
        pass

    @thrift_client_call
    def getLinesInSourceFileContents(self, lines_in_files_requested, encoding):
        pass

    @thrift_client_call
    def getDiffResultsHash(self, run_ids, report_hashes, diff_type,
                           skip_detection_statuses, tag_ids):
        pass

    @thrift_client_call
    def getRunResultTypes(self, runId, reportFilters):
        pass

    @thrift_client_call
    def removeRunResults(self, run_ids):
        pass

    @thrift_client_call
    def removeRunReports(self, run_ids, report_filter, cmp_data):
        pass

    @thrift_client_call
    def removeRun(self, run_id, run_filter):
        pass

    @thrift_client_call
    def updateRunData(self, run_id, new_run_name):
        pass

    @thrift_client_call
    def getSuppressedBugs(self, run_id):
        pass

    @thrift_client_call
    def getNewResults(self, base_run_id, new_run_id, limit, offset, sortType,
                      reportFilters):
        pass

    @thrift_client_call
    def getUnresolvedResults(self, base_run_id, new_run_id, limit, offset,
                             sortType, reportFilters):
        pass

    @thrift_client_call
    def getResolvedResults(self, base_run_id, new_run_id, limit, offset,
                           sortType, reportFilters):
        pass

    @thrift_client_call
    def changeReviewStatus(self, report_id, status, message):
        pass

    @thrift_client_call
    def changeReviewStatusByHash(self, bug_hash, status, message):
        pass

    # pylint: disable=redefined-builtin
    @thrift_client_call
    def getReviewStatusRules(self, filter, sortMode, limit, offset):
        pass

    @thrift_client_call
    def getRunResults(self, runIds, limit, offset, sortType, reportFilter,
                      cmpData, getDetails):
        pass

    @thrift_client_call
    def getReportAnnotations(self, key):
        pass

    @thrift_client_call
    def getRunResultCount(self, runIds, reportFilter, cmpData):
        pass

    @thrift_client_call
    def getSeverityCounts(self, runIds, reportFilter, cmpData):
        pass

    @thrift_client_call
    def getCheckerMsgCounts(self, runIds, reportFilter, cmpData, limit,
                            offset):
        pass

    @thrift_client_call
    def getReviewStatusCounts(self, runIds, reportFilter, cmpData):
        pass

    @thrift_client_call
    def getDetectionStatusCounts(self, runIds, reportFilter, cmpData):
        pass

    @thrift_client_call
    def getFileCounts(self, runIds, reportFilter, cmpData, limit, offset):
        pass

    @thrift_client_call
    def getCheckerCounts(self, base_run_ids, reportFilter, cmpData, limit,
                         offset):
        pass

    @thrift_client_call
    def exportData(self, runId):
        pass

    @thrift_client_call
    def importData(self, exportData):
        pass
    # SOURCE COMPONENT RELATED API CALLS

    @thrift_client_call
    def addSourceComponent(self, name, value, description):
        pass

    @thrift_client_call
    def getSourceComponents(self, component_filter):
        pass

    @thrift_client_call
    def removeSourceComponent(self, name):
        pass

    # STORAGE RELATED API CALLS

    @thrift_client_call
    def getMissingContentHashes(self, file_hashes):
        pass

    @thrift_client_call
    def getMissingContentHashesForBlameInfo(self, file_hashes):
        pass

    @thrift_client_call
    def massStoreRun(self, name, tag, version, zipdir, force,
                     trim_path_prefixes, description):
        pass

    @thrift_client_call
    def massStoreRunAsynchronous(self, zipfile_blob: str,
                                 store_opts: ttypes.SubmittedRunOptions) \
            -> str:
        pass

    @thrift_client_call
    def allowsStoringAnalysisStatistics(self):
        pass

    @thrift_client_call
    def getAnalysisStatisticsLimits(self):
        pass

    @thrift_client_call
    def getAnalysisStatistics(self, run_id, run_history_id):
        pass

    @thrift_client_call
    def storeAnalysisStatistics(self, run_name, zip_file):
        pass
