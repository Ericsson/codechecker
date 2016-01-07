// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
], function (declare) {

  /**
   * This class contains various utility functions. It is instanciated once in
   * the global namespace as CC_UTIL
   */

return declare(null, {


  /**
   * Queries and formats the result types available for a Run. After these, it
   * executes the callback function with the formatted results as the parameter.
   * The function is asyncronous.
   */
  getCheckerInfoRun : function (runId, filePath, suppressed, callback) {
    var that = this;

    var filter = new codeCheckerDBAccess.ReportFilter();
    filter.filepath = filePath;
    filter.suppressed = suppressed;

    CC_SERVICE.getRunResultTypes(
      runId,
      [filter],
      function (reportDataTypeCountList) {
        if (reportDataTypeCountList instanceof RequestFailed) {
          console.error("Thrift API call 'getRunResultTypes' failed.");
          return;
        }

        callback(that.parseReportDataTypeCounts(reportDataTypeCountList));
      }
    );
  },


  /**
   * Queries and formats the result types available for a Diff. After these, it
   * executes the callback function with the formatted results as the parameter.
   * The function is asyncronous.
   */
  getCheckerInfoDiff : function (baseRunId, newRunId, filePath, suppressed, resolvedState, callback) {
    var that = this;

    var filter = new codeCheckerDBAccess.ReportFilter();
    filter.filepath = filePath;
    filter.suppressed = suppressed;

    var diffType = null;

    switch (resolvedState) {
      case "newonly" : diffType = codeCheckerDBAccess.DiffType.NEW; break;
      case "resolv"  : diffType = codeCheckerDBAccess.DiffType.RESOLVED; break;
      case "unresolv": diffType = codeCheckerDBAccess.DiffType.UNRESOLVED; break;
    }

    CC_SERVICE.getDiffResultTypes(
      baseRunId,
      newRunId,
      diffType,
      [filter],
      function (reportDataTypeCountList) {
        if (reportDataTypeCountList instanceof RequestFailed) {
          console.error("Thrift API call 'getDiffResultTypes' failed.");
          return;
        }

        callback(that.parseReportDataTypeCounts(reportDataTypeCountList));
      }
    );
  },


  /**
   * Transforms the result of a getRunResultTypes API query to a processable
   * format.
   * The output format is:
   *   {
   *     ALL      : { name : "All" , count : 20 , checkers : {} },
   *     CRITICAL : { name : "Critical" , count : 10 , checkers : { core.something : 5 , unix.checker : 5 } },
   *     HIGH     : ...
   *     ....     : ...
   *   }
   */
  parseReportDataTypeCounts : function (reportDataTypeCountList) {
    var that = this;

    var checkerInfo = {};

    for (var key in Severity) {
      var severityStringLowerCase = key.toLowerCase();
      var severityString = severityStringLowerCase.charAt(0).toUpperCase() +
        severityStringLowerCase.slice(1);

      checkerInfo[Severity[key]] =
        { name : severityString , count : 0 , checkers : {} };
    }

    reportDataTypeCountList.forEach(function (e,i) {
      checkerInfo[e.severity].count += e.count;
      checkerInfo[e.severity].checkers[e.checkerId] = e.count;
    });

    var checkerInfoOrderedKeys = Object.keys(checkerInfo).sort(function (a, b) {
      return parseInt(b) - parseInt(a);
    });

    var newCheckerInfo = { "ALL" : { "name" : "All" , "count" : 0 , "checkers" : {} } };

    checkerInfoOrderedKeys.forEach(function (e,i) {
      newCheckerInfo[that.severityValueToKey(e)] = checkerInfo[e];
      newCheckerInfo.ALL.count += checkerInfo[e].count;
    });

    return newCheckerInfo;
  },


  /**
   * Normalizes a formatted reportDataTypeCountList, after which it can be
   * used in a Dojo Select widget.
   */
  normalizeCheckerInfo : function (checkerInfo) {
    var selectOptions = [];

    for (var key in checkerInfo) {
      var e = checkerInfo[key];

      if (key === "ALL") {
        selectOptions.push({
          "label" : e.name + " (" + e.count + ")" ,
          "value" : "all"
        });
      } else if (e.count > 0) {
        selectOptions.push({
          "label" : e.name + " (" + e.count + ")" ,
          "value" : "severity##" + Severity[key]
        });

        for (var checkerKey in e.checkers) {
          selectOptions.push({
            "label" : "&nbsp;&nbsp;&nbsp;&nbsp;" + checkerKey + " (" + e.checkers[checkerKey] + ")" ,
            "value" : "checker##" + checkerKey
          });
        }
      }
    }

    return selectOptions;
  },


  /**
   * Gets the enum key for a severity code.
   */
  severityValueToKey : function (value) {
    for (var key in Severity) {
      if (Severity[key] == value) { return key; }
    }
  },


  /**
   * Converts a Thrift API severity id to human readable string.
   *
   * @param severityCode Thrift API severity id
   * @return human readable severity string
   */
  severityFromCodeToString : function (severityCode) {
    if (severityCode === "all"){
      return "All";
    }

    for (var key in Severity) {
      if (Severity[key] === parseInt(severityCode)){
        return key.toLowerCase();
      }
    }

    return null;
  },


  /**
   * Converts a severity string to Thrift API severity id.
   *
   * @param severityString severity as string
   * @return severity as number (id)
   */
  severityFromStringToCode : function (severityString) {
    return Severity[severityString.toUpperCase()];
  },


  /**
   * Returns overview DOM id for the given browser hash state.
   *
   * @param hashState browser hash state object
   * @return DOM id string or undefined
   */
  getOverviewIdFromHashState : function (hashState) {
    if (hashState.ovType == 'run') {
      return "runoverviewtc_" + hashState.ovRunId;
    } else if (hashState.ovType == 'diff') {
      return "diffoverviewtc_" + hashState.diffRunIds[0] + "_" +  hashState.diffRunIds[1];
    } else if (JSON.stringify(hashState) == "{}") {
      return "bc_listofrunsgrid";
    }

    return undefined;
  }
});});
