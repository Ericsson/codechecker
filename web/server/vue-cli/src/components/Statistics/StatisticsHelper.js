import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter, ReviewStatus } from "@cc/report-server-types";

function resultToNumber(value) {
  if (value === undefined) return 0;

  if (Number.isInteger(value))
    return value;

  return value.count !== undefined ? value.count.toNumber() : value.toNumber();
}

function initDiffField(count) {
  return { count: resultToNumber(count), new: null, resolved: null };
}

function getCheckerStatistics(runIds, reportFilter, cmpData) {
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

    return checkerNames.map(key => {
      const outstanding = (res[1][key]?.count || 0) +
        (res[2][key]?.count || 0);

      const suppressed = (res[3][key]?.count || 0) +
        (res[4][key]?.count || 0);

      return {
        checker       : key,
        severity      : checkers[key].severity,
        reports       : initDiffField(checkers[key]),
        unreviewed    : initDiffField(res[1][key]),
        confirmed     : initDiffField(res[2][key]),
        outstanding   : initDiffField(outstanding),
        falsePositive : initDiffField(res[3][key]),
        intentional   : initDiffField(res[4][key]),
        suppressed    : initDiffField(suppressed),
      };
    });
  });
}

function getSeverityStatistics(runIds, reportFilter, cmpData) {
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
      ccService.getClient().getSeverityCounts(runIds, filter, cmpData,
        handleThriftError(severityCounts => {
          resolve(severityCounts);
        }));
    });
  });

  return Promise.all(queries).then(res => {
    return Object.keys(res[0]).map(key => {
      const outstanding = (res[1][key] || 0) + (res[2][key] || 0);
      const suppressed = (res[3][key] || 0) + (res[4][key] || 0);

      return {
        severity      : parseInt(key),
        reports       : initDiffField(res[0][key]),
        unreviewed    : initDiffField(res[1][key]),
        confirmed     : initDiffField(res[2][key]),
        outstanding   : initDiffField(outstanding),
        falsePositive : initDiffField(res[3][key]),
        intentional   : initDiffField(res[4][key]),
        suppressed    : initDiffField(suppressed),
      };
    });
  });
}

function getComponents() {
  return new Promise(resolve => {
    ccService.getClient().getSourceComponents(null,
      handleThriftError(components =>
        resolve(components)));
  });
}

async function getComponentStatistics(component, runIds, reportFilter,
  cmpData
) {
  const filter = new ReportFilter(reportFilter);
  filter["reviewStatus"] = null;
  filter["componentNames"] = [ component.name ];

  const res = await new Promise(resolve =>
    ccService.getClient().getReviewStatusCounts(runIds, filter, cmpData,
      handleThriftError(res => resolve(res))));

  const outstanding = (res[ReviewStatus.UNREVIEWED]?.toNumber() || 0) +
    (res[ReviewStatus.CONFIRMED]?.toNumber() || 0);

  const suppressed = (res[ReviewStatus.FALSE_POSITIVE]?.toNumber() || 0) +
    (res[ReviewStatus.INTENTIONAL]?.toNumber() || 0);

  const reports = Object.keys(res).reduce((acc, curr) => {
    acc += res[curr].toNumber();
    return acc;
  }, 0);

  return {
    reports       : reports,
    unreviewed    : res[ReviewStatus.UNREVIEWED],
    confirmed     : res[ReviewStatus.CONFIRMED],
    outstanding   : outstanding,
    falsePositive : res[ReviewStatus.FALSE_POSITIVE],
    intentional   : res[ReviewStatus.INTENTIONAL],
    suppressed    : suppressed
  };
}

export {
  getCheckerStatistics,
  getComponents,
  getComponentStatistics,
  getSeverityStatistics,
  initDiffField,
  resultToNumber
};
