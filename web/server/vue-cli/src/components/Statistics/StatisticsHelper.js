
import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter, ReviewStatus } from "@cc/report-server-types";

function resultToNumber(value) {
  if (value === undefined) return 0;

  return value.count !== undefined ? value.count.toNumber() : value.toNumber();
}

function getCheckerStatistics(runIds, reportFilter) {
  const cmpData = null;
  const limit = null;
  const offset = null;

  const queries = [
    { field: null, values: null },
    { field: "reviewStatus", values: [ ReviewStatus.UNREVIEWED ] },
    { field: "reviewStatus", values: [ ReviewStatus.CONFIRMED ] },
    { field: "reviewStatus", values: [ ReviewStatus.FALSE_POSITIVE ] },
    { field: "reviewStatus", values: [ ReviewStatus.INTENTIONAL ] }
  ].map(q => {
    const filter = new ReportFilter(reportFilter);

    if (q.field) {
      filter[q.field] = q.values;
    }

    return new Promise(resolve => {
      ccService.getClient().getCheckerCounts(runIds, filter, cmpData,
        limit, offset, handleThriftError(checkerCounts => {
          const obj = {};
          checkerCounts.forEach(item => { obj[item.name] = item; });
          resolve(obj);
        }));
    });
  });

  return Promise.all(queries).then(res => {
    const checkers = res[0];
    const checkerNames = Object.keys(checkers);

    return checkerNames.map(key => ({
      checker       : key,
      severity      : checkers[key].severity,
      reports       : checkers[key].count.toNumber(),
      unreviewed    : resultToNumber(res[1][key]),
      confirmed     : resultToNumber(res[2][key]),
      falsePositive : resultToNumber(res[3][key]),
      intentional   : resultToNumber(res[4][key])
    }));
  });
}

function getComponents() {
  return new Promise(resolve => {
    ccService.getClient().getSourceComponents(null,
      handleThriftError(components =>
        resolve(components)));
  });
}

async function getComponentStatistics(component, runIds, reportFilter) {
  const cmpData = null;

  const queries = [
    { field: null, values: null },
    { field: "reviewStatus", values: [ ReviewStatus.UNREVIEWED ] },
    { field: "reviewStatus", values: [ ReviewStatus.CONFIRMED ] },
    { field: "reviewStatus", values: [ ReviewStatus.FALSE_POSITIVE ] },
    { field: "reviewStatus", values: [ ReviewStatus.INTENTIONAL ] }
  ].map(q => {
    const filter = new ReportFilter(reportFilter);

    if (q.field) {
      filter[q.field] = q.values;
    }

    filter["componentNames"] = [ component ];

    return new Promise(resolve => {
      ccService.getClient().getRunResultCount(runIds, filter, cmpData,
        handleThriftError(resultCount => resolve(resultCount)));
    });
  });

  return Promise.all(queries);
}

export {
  getCheckerStatistics,
  getComponents,
  getComponentStatistics,
  resultToNumber
};
