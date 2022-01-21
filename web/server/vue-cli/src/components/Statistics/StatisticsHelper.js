import { ccService, handleThriftError } from "@cc-api";
import { ReportFilter, ReviewStatus } from "@cc/report-server-types";

const reviewStatusVariations = [
  { field: null, values: null },
  { field: "reviewStatus", values: [ ReviewStatus.UNREVIEWED ] },
  { field: "reviewStatus", values: [ ReviewStatus.CONFIRMED ] },
  { field: "reviewStatus", values: [ ReviewStatus.FALSE_POSITIVE ] },
  { field: "reviewStatus", values: [ ReviewStatus.INTENTIONAL ] },
  { field: "reviewStatus", values: [
    ReviewStatus.UNREVIEWED,
    ReviewStatus.CONFIRMED ] },
  { field: "reviewStatus", values: [
    ReviewStatus.FALSE_POSITIVE,
    ReviewStatus.INTENTIONAL ] }
];

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

  const queries = reviewStatusVariations.map(q => {
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
      return {
        checker       : key,
        severity      : checkers[key].severity,
        reports       : initDiffField(checkers[key]),
        unreviewed    : initDiffField(res[1][key]),
        confirmed     : initDiffField(res[2][key]),
        outstanding   : initDiffField(res[5][key]),
        falsePositive : initDiffField(res[3][key]),
        intentional   : initDiffField(res[4][key]),
        suppressed    : initDiffField(res[6][key]),
      };
    });
  });
}

function getSeverityStatistics(runIds, reportFilter, cmpData) {
  const queries = reviewStatusVariations.map(q => {
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
      return {
        severity      : parseInt(key),
        reports       : initDiffField(res[0][key]),
        unreviewed    : initDiffField(res[1][key]),
        confirmed     : initDiffField(res[2][key]),
        outstanding   : initDiffField(res[5][key]),
        falsePositive : initDiffField(res[3][key]),
        intentional   : initDiffField(res[4][key]),
        suppressed    : initDiffField(res[6][key]),
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

  const queries = [
    [ ReviewStatus.UNREVIEWED, ReviewStatus.CONFIRMED ],
    [ ReviewStatus.FALSE_POSITIVE, ReviewStatus.INTENTIONAL ],
    null
  ].map(status => {
    return new Promise(resolve => {
      filter["reviewStatus"] = status;
      return ccService.getClient().getRunResultCount(runIds, filter, cmpData,
        handleThriftError(res => resolve(res)));
    });
  });

  const runResCounts = await Promise.all(queries);

  return {
    reports       : runResCounts[2]?.toNumber() || 0,
    unreviewed    : res[ReviewStatus.UNREVIEWED],
    confirmed     : res[ReviewStatus.CONFIRMED],
    outstanding   : runResCounts[0]?.toNumber() || 0,
    falsePositive : res[ReviewStatus.FALSE_POSITIVE],
    intentional   : res[ReviewStatus.INTENTIONAL],
    suppressed    : runResCounts[1]?.toNumber() || 0
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
