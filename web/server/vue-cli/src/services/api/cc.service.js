import ServiceClient from "@cc/db-access";
import {
  MAX_QUERY_SIZE,
  Order,
  ReportFilter,
  RunFilter,
  RunHistoryFilter,
  SortMode,
  SortType
} from "@cc/report-server-types";

import { BaseService, handleThriftError } from "./_base.service";

function extractTagWithRunName(runWithTagName) {
  const index = runWithTagName.indexOf(":");

  let runName, tagName;
  if (index !== -1) {
    runName = runWithTagName.substring(0, index);
    tagName = runWithTagName.substring(index + 1);
  } else {
    tagName = runWithTagName;
  }

  return { runName, tagName };
}

class CodeCheckerService extends BaseService {
  constructor() {
    super("CodeCheckerService", ServiceClient);
  }

  getSameReports(bugHash) {
    const reportFilter = new ReportFilter({ reportHash: [ bugHash ] });

    const sortMode = new SortMode({
      type: SortType.FILENAME,
      ord: Order.ASC
    });

    return new Promise(resolve => {
      this.getClient().getRunResults(null, MAX_QUERY_SIZE, 0,
        [ sortMode ], reportFilter, null, false,
        handleThriftError(reports => {
          const runIds = reports.map(report => report.runId);
          this.getRuns(runIds).then(runs => {
            resolve(reports.map(report => {
              const run =
                runs.find(run => run.runId.equals(report.runId)) || {};

              return {
                ...report,
                "$runName": run.name
              };
            }));
          });
        }));
    });
  }

  getRuns(runIds) {
    const runFilter = new RunFilter({ ids: runIds });

    return new Promise(resolve => {
      this.getClient().getRunData(runFilter, null, 0, null,
        handleThriftError(res => {
          resolve(res);
        }));
    });
  }

  getRunIds(runName) {
    const runFilter = new RunFilter({ names: [ runName ] });
    const limit = null;
    const offset = null;
    const sortMode = null;

    return new Promise(resolve => {
      this.getClient().getRunData(runFilter, limit, offset, sortMode,
        handleThriftError(runs => {
          resolve(runs.map(run => run.runId.toNumber() ));
        }));
    });
  }

  async getTags(runIds, tagIds, tagNames, stored) {
    const limit = null;
    const offset = 0;

    const runHistoryFilter = new RunHistoryFilter({
      tagIds,
      tagNames,
      stored
    });

    return new Promise(resolve => {
      this.getClient().getRunHistory(runIds, limit, offset,
        runHistoryFilter, handleThriftError(res => {
          resolve(res);
        }));
    });
  }

  /**
   * Get code coverage data for a specific file
   * @param {number} fileId - The ID of the file to get coverage for
   * @param {Array<number>} runIds - Array of run IDs to get coverage from
   * @returns {Promise<Object>} - Returns promise that resolves to coverage data
   * @example
   * {
   *   fileId: 123,
   *   filePath: "/path/to/file.cpp",
   *   totalLines: 100,
   *   coveredLines: 80,
   *   uncoveredLines: 20,
   *   coveragePercentage: 80,
   *   lineCoverage: [
   *     {
   *       lineNumber: 1,
   *       covered: true,
   *       executionCount: 5,
   *       lastExecution: "2024-04-20T10:00:00Z"
   *     },
   *     {
   *       lineNumber: 2,
   *       covered: false,
   *       executionCount: 0,
   *       lastExecution: null
   *     }
   *   ]
   * }
   */
  getCodeCoverage(fileId, runIds) {
    return new Promise(resolve => {
      this.getClient().getCodeCoverage(
        fileId,
        runIds,
        handleThriftError(coverageData => {
          resolve(coverageData);
        })
      );
    });
  }
}

const ccService = new CodeCheckerService();

export {
  ccService as default,
  extractTagWithRunName
};
