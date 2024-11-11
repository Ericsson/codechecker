/**
 * Parse the given url hash parameter and returns a map.
 * @param {string} hash 
 * 
 * E.g.: #review-status=Unreviewed&tab=statistics
 */
function parseHash(hash) {
  const res = {};

  hash = hash.replace(/^#/, "");

  if (!hash) {
    return res;
  }

  hash.split("&").forEach(param => {
    const parts = param.split("=");
    const key = decodeURIComponent(parts.shift());
    const val = parts.length > 0
      ? decodeURIComponent(parts.join("="))
      : null;

    if (res[key] === undefined) {
      res[key] = val;
    } else if (Array.isArray(res[key])) {
      res[key].push(val);
    } else {
      res[key] = [ res[key], val ];
    }
  });

  return res;
}

// Maps old query parameter names to new names.
const oldParamsToNew = {
  "difftype": "diff-type",
  "report": "report-id",
  "reportHash": "report-hash"
};

/**
 * Converts the given route parameters to new url format.
 * @param {Route} to 
 */
export default function convertOldUrlToNew(route) {
  // If hash is not set then it is a new url.
  if (!route.hash) return;

  const hash = parseHash(route.hash);

  // If the url does not contain a tab key in the hash parameter then it is
  // a new url too.
  if (!hash.tab && !hash.subtab) return;

  let name = route.name;
  const { tab, subtab, ...query } = hash;

  if (subtab) {
    if (subtab === "runHistory") {
      name = "run-history";
    } else {
      name = "report-detail";
    }
  } else if (tab) {
    if (tab === "allReports") {
      name = "reports";
    } else if (tab === "statistics") {
      name = "statistics";
    } else if (tab === "changelog") {
      name = "new-features";
    } else if (tab === "userguide") {
      name = "userguide";
    } else {
      name = "runs";
    }
  }

  // Rename old parameters.
  Object.keys(oldParamsToNew).forEach(key => {
    if (query[key] !== undefined) {
      query[oldParamsToNew[key]] = query[key];
      delete query[key];
    }
  });

  return {
    "name": name,
    "params": route.params,
    "query": query,
  };
}
