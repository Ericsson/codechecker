import { Client as ServiceClient } from "@cc/db-access";
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
          const runFilter = new RunFilter({
            ids: reports.map(report => report.runId)
          });
          this.getRuns(runFilter).then(runs => {
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

  async getRuns(runFilter, sortMode) {
    const runs = [];
    let offset = 0;

    while (true) {
      const r = await new Promise(resolve => {
        this.getClient().getRunData(
          runFilter, MAX_QUERY_SIZE, offset, sortMode,
          handleThriftError(res => {
            resolve(res);
          }));
      });

      runs.push(...r);

      if (r.length < MAX_QUERY_SIZE)
        break;

      offset += MAX_QUERY_SIZE;
    }

    return runs;
  }

  async getRunIds(runName) {
    const runFilter = new RunFilter({ names: [ runName ] });
    const runs = await this.getRuns(runFilter);
    return runs.map(run => run.runId.toNumber());
  }

  async getTags(runIds, tagIds, tagNames, stored) {
    const limit = MAX_QUERY_SIZE;
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
