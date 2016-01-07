// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/kernel",
  "dojo/_base/declare",
  "dojo/Deferred",
  "dojo/store/util/QueryResults",
  "dojo/promise/all"
], function (kernel, declare, Deferred, QueryResults, promiseAll) {
  /**
   * A store implementation for OverviewGrid. It implements dojo/api/Store. You
   * should wrap it using an ObjectStore (or something else) to be able to use
   * it with a DataGrid (since a DataGrid uses dojo/data API).
   *
   * Query and get operations implemented using Thrift async API. It's a read
   * only store.
   *
   * Query options format (common):
   *   Standard dojo/api/Store query options format. In sort array only a few
   *   attribute kind allowed (see _attributeToSortType for details)
   *
   * Query format for run overview:
   *   query.overviewType: should be something which equals to "run" as string
   *   query.runId: a run id (could be string or number or even regex)
   *   query.filters: codeCheckerDBAccess friendly filters
   *
   * Query format for diff view:
   *   query.overviewType: should be something which equals to "diff" as string
   *   query.runId1: baseline run id
   *   query.runId2: new run id
   *   query.filters: codeCheckerDBAccess friendly filters
   */
return declare(null, {


   /**
    * Maps sort ids to codeCheckerDBAccess Thrift API sort types.
    */
  _attributeToSortType : {
    fileWithBugPos : codeCheckerDBAccess.SortType.FILENAME,
    checkerId      : codeCheckerDBAccess.SortType.CHECKER_NAME,
    severity       : codeCheckerDBAccess.SortType.SEVERITY
  },


  /**
   * Simple constructor. No parameters.
   */
  constructor : function (options) {
    declare.safeMixin(this, options);
  },


  /**
   * Converts Dojo Store API sort array to codeCheckerDBAccess sort array for
   * get{New|Resolved|Unresolved}Results and getRunResults calls.
   *
   * @param sorts Dojo Store API sort array
   * @return codeCheckerDBAccess sort array
   */
  _convertSorts : function (sorts) {
    var that = this;
    result = [];

    sorts.forEach(function (item) {
      var sortMode = new codeCheckerDBAccess.SortMode();
      sortMode.ord = item.descending ?
        codeCheckerDBAccess.Order.DESC : codeCheckerDBAccess.Order.ASC;
      sortMode.type = that._attributeToSortType[item.attribute];
      if (sortMode.type === undefined) {
        console.error("Unknown sort attribute: ", item.attribute);
        return;
      }

      result.push(sortMode);
    });

    return result;
  },


  /**
   * Queries run results using the provided filters (query.filters) and sorts.
   *
   * @param query a query in run overview format
   * @param options query options
   * @param sorts sort array in codeCheckerDBAccess format (see _convertSorts)
   * @return a Deferred to a result array
   */
  _queryRun : function (query, options, sorts) {
    var that     = this;
    var deferred = new Deferred();

    CC_SERVICE.getRunResults(
      query.runId,
      options.count,
      options.start,
      sorts,
      query.filters,
      function (reportDataList) {
        if (reportDataList instanceof RequestFailed) {
          deferred.reject("Failed to get reports: " + reportDataList.message);
        } else {
          deferred.resolve(that._formatItems(reportDataList, query.runId));
        }
      }
    );

    return deferred;
  },


  /**
   * Queries new results for a diff view (helper method for _queryDiff).
   *
   * @param query a query in diff view format
   * @param options query options
   * @param sorts sort array in codeCheckerDBAccess format (see _convertSorts)
   * @return a Deferred to a result array
   */
  _queryDiffNewResults : function (query, options, sorts) {
    var that     = this;
    var deferred = new Deferred();

    if (query.newResultsFilters.length > 0) {
      CC_SERVICE.getNewResults(
        query.runId1,
        query.runId2,
        codeCheckerDBAccess.MAX_QUERY_SIZE,
        0,
        sorts,
        query.newResultsFilters,
        function (reportDataList) {
          if (reportDataList instanceof RequestFailed) {
            deferred.reject("Failed to get reports: " + reportDataList.message);
          } else {
            deferred.resolve(that._formatItems(reportDataList, query.runId2));
          }
        }
      );
    } else {
      deferred.resolve([]);
    }

    return deferred;
  },


  /**
   * Queries new results for a diff view (helper method for _queryDiff).
   *
   * @param query a query in diff view format
   * @param options query options
   * @param sorts sort array in codeCheckerDBAccess format (see _convertSorts)
   * @return a Deferred to a result array
   */
  _queryDiffResolvedResults : function (query, options, sorts) {
    var that     = this;
    var deferred = new Deferred();

    if (query.resolvedResultsFilters.length > 0) {
      CC_SERVICE.getResolvedResults(
        query.runId1,
        query.runId2,
        codeCheckerDBAccess.MAX_QUERY_SIZE,
        0,
        sorts,
        query.resolvedResultsFilters,
        function (reportDataList) {
          if (reportDataList instanceof RequestFailed) {
            deferred.reject("Failed to get reports: " + reportDataList.message);
          } else {
            deferred.resolve(that._formatItems(reportDataList, query.runId1));
          }
        }
      );
    } else {
      deferred.resolve([]);
    }

    return deferred;
  },


  /**
   * Queries new results for a diff view (helper method for _queryDiff).
   *
   * @param query a query in diff view format
   * @param options query options
   * @param sorts sort array in codeCheckerDBAccess format (see _convertSorts)
   * @return a Deferred to a result array
   */
  _queryDiffUnresolvedResults : function (query, options, sorts) {
    var that     = this;
    var deferred = new Deferred();

    if (query.unresolvedResultsFilters.length > 0) {
      CC_SERVICE.getUnresolvedResults(
        query.runId1,
        query.runId2,
        codeCheckerDBAccess.MAX_QUERY_SIZE,
        0,
        sorts,
        query.unresolvedResultsFilters,
        function (reportDataList) {
          if (reportDataList instanceof RequestFailed) {
            deferred.reject("Failed to get reports: " + reportDataList.message);
          } else {
            deferred.resolve(that._formatItems(reportDataList, query.runId2));
          }
        }
      );
    } else {
      deferred.resolve([]);
    }

    return deferred;
  },


  /**
   * Queries run results for a diff view using _queryDiffNewResults,
   * _queryDiffResolvedResults, and _queryDiffUnresolvedResults.
   *
   * @param query a query in diff view format
   * @param options query options
   * @param sorts sort array in codeCheckerDBAccess format (see _convertSorts)
   * @return a Deferred to a result array
   */
  _queryDiff : function (query, options, sorts) {
    var that          = this;
    var deferred      = new Deferred();
    var resultList    = [];

    promiseAll([
      that._queryDiffNewResults(query, options, sorts),
      that._queryDiffResolvedResults(query, options, sorts),
      that._queryDiffUnresolvedResults(query, options, sorts)
    ]).then(
      function (reportDataLists) {
        deferred.resolve(reportDataLists[0].concat(reportDataLists[1]).
          concat(reportDataLists[2]));
      },
      function (error) {
        deferred.reject(error);
      });

    return deferred;
  },


  /**
   * Calls _formatItem on all elements in the given report array and returns a
   * new list with the results. It keeps the original order.
   *
   * @param reportDataList array of ReportData
   * @param runId run id for reports
   * @return a new array with DataGrid friendly items.
   */
  _formatItems : function (reportDataList, runId) {
    var that = this;

    var endResult = [];
    reportDataList.forEach(function (reportData) {
      endResult.push(that._formatItem(reportData, runId));
    });

    return endResult;
  },


  /**
   * Converts a ReportData to a DataGrid friendly item. Adds fileWithBugPos and
   * runId attributes and converts severity to human readable string.
   *
   * @param reportData a raw ReportData
   * @param runId run id for the report
   * @return the same reportData but with the new/updated fields.
   */
  _formatItem : function (reportData, runId) {
    reportData.severity = CC_UTIL.severityFromCodeToString(reportData.severity);
    reportData.fileWithBugPos = reportData.checkedFile + "\n@ Line " +
      reportData.lastBugPosition.startLine;
    reportData.runId = runId;

    if (reportData.suppressComment === null) {
      reportData.suppressComment = "---";
    }

    return reportData;
  },


  /**
   * Return whether the given attribute is usable for sorting or not.
   *
   * @param attribute an attribute string
   * @return return true if the attribute can be in the sort array, false if not
   */
  canSortByAttribute : function (attribute) {
    return this._attributeToSortType[attribute] !== undefined;
  },


  /**
   * See dojo/api/Store.
   */
  getIdentity : function (reportData) {
    return reportData.reportId;
  },


  /**
   * Queries a ReportData by report id. Currently this method is not called by
   * anyone.
   *
   * @param id a report id
   * @return a Deferred to a ReportData
   */
  get : function (id) {
    var deferred = new Deferred();

    CC_SERVICE.getReport(parseInt(id), function (reportData){
      if (typeof reportData === "string") {
        deferred.reject("Failed to get report " + id + ": " + reportData);
      } else {
        deferred.resolve(reportData);
      }
    });

    return deferred;
  },


  /**
   * The main entry point: runs a query.
   *
   * @param query a query in diff view or overview format (see above)
   * @param options an object in query options format (see above)
   * @return a QueryResults
   */
  query : function (query, options) {
    var that = this;

    options = options || {};
    options.start = options.start || 0;
    options.count = options.count || codeCheckerDBAccess.MAX_QUERY_SIZE;
    options.sort  = options.sort  || [];

    if (options.defaultSort) {
      // merge default sort options
      options.defaultSort.forEach(function (item) {
        var overridden = options.sort.filter(function (sortItem) {
          return sortItem.attribute === item.attribute;
        });

        if (overridden.length === 0) {
          options.sort.push(item);
        }
      });
    }

    var ovType = String(query.overviewType);
    var results;
    if (ovType === "run") {
      results = that._queryRun(query, options,
        that._convertSorts(options.sort));
    } else if (ovType === "diff") {
      results = that._queryDiff(query, options,
        that._convertSorts(options.sort));
    } else {
      console.error("Bad overview type: " + query.overviewType);
      return [];
    }

    results.total = options.total;

    return QueryResults(results);
  },


  put : function (object, directives) {
    // not supported
  },


  add : function (object, directives) {
    // not supported
  },


  remove : function (id) {
    // not supported
  },


  transaction : function () {
    // not supported
  },


  getChildren : function (parent, options) {
    // not supported
  },


  getMetadata : function (object) {
    // not supported
  }


});});
