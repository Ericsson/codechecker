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
}

const ccService = new CodeCheckerService();

export {
  ccService as default,
  extractTagWithRunName
};
