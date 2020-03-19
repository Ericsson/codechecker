import ServiceClient from "@cc/db-access";
import {
  MAX_QUERY_SIZE,
  Order,
  ReportFilter,
  RunFilter,
  SortMode,
  SortType
} from "@cc/report-server-types";

import { BaseService, handleThriftError } from "./_base.service";

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
}

const ccService = new CodeCheckerService();

export default ccService;
