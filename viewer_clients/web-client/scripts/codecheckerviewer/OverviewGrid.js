// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/data/ObjectStore",
  "dojo/Deferred",
  "dojox/grid/DataGrid",
  "ccvscripts/OverviewStore",
], function (declare, ObjectStore, Deferred, DataGrid, OverviewStore) {
return declare(DataGrid, {


  /**
   * Construct the new object. The following arguments are required:
   *   myOverviewTC: The OverviewTC this object belongs to
   */
  constructor : function (args) {
    var that = this;
    declare.safeMixin(that, args);

    that.ovStore   = new OverviewStore({});
    that.store     = new ObjectStore({objectStore: that.ovStore});
    that.cellWidth = ((100)/5).toString() + "%";

    that.structure = [
      { name : "File", field : "fileWithBugPos", styles : "text-align: center;", width : that.cellWidth , formatter : function (data) { return data.split('\n').join('<br/>'); } },
      { name : "Message", field : "checkerMsg", styles : "text-align: center;", width : that.cellWidth },
      { name : "Checker name", field : "checkerId", styles : "text-align: center;", width : that.cellWidth },
      { name : "Severity", field : "severity", styles : "text-align: center;", width : that.cellWidth },
      { name : "Suppress Comment", field : "suppressComment", styles : "text-align: center;", width : that.cellWidth },
    ];

    marked.setOptions({ highlight: function (code) { return hljs.highlightAuto(code).value; } });
  },


  postCreate : function () {
    var that = this;
    that.inherited(arguments);

    that.refreshGrid();
  },


  /**
   * Returns whether sorting is allowed or not for the given cell.
   *
   * For parameters see dojox/grid/DataGrid documentation.
   */
  canSort : function (inSortInfo) {
    var that = this;
    var cell = that.getCell(Math.abs(inSortInfo)-1);
    if (!cell) {
      return false;
    }

    if (that.ovStore.canSortByAttribute(cell.field)) {
      return that.inherited(arguments);
    }

    return false;
	},


  /**
   * Returns the default sort options.
   *
   * @return the default sort array
   */
  _getDefaultSortOptions : function () {
    return [
      {
        attribute : "severity",
        descending: true
      },
      {
        attribute : "checkerId",
        descending: false
      },
      {
        attribute : "fileWithBugPos",
        descending: false
      }
    ];
  },


  /**
   * Creates a new Run view query object using the given filter settings.
   * This is a helper method for _createQuery.
   *
   * @param runFilters Filters (see OverviewGrid::_createRunApiFilters)
   * @param count The hit count a query with the gives filters produces.
   * @return a new query object.
   */
  _createRunOverviewQuery : function (runFilters, count) {
    var that = this;
    var query = {
      overviewType : "run",
      runId        : that.myOverviewTC.runId,
      filters      : runFilters,
      defaultSort  : that._getDefaultSortOptions(),
      total        : count,
    };

    return query;
  },


  /**
   * Creates a new Diff view query object using the given filter settings. This
   * is a helper method for _createQuery.
   *
   * @param diffFiltersObj The three Diff filter arrays in an object
   * (see OverviewGrid::_createDiffApiFilters)
   * @param count The hit count a query with the gives filters produces.
   * @return a new query object.
   */
  _createDiffOverviewQuery : function (diffFiltersObj, count) {
    var that = this;

    var query = {
      overviewType             : "diff",
      runId1                   : that.myOverviewTC.runId1,
      runId2                   : that.myOverviewTC.runId2,
      newResultsFilters        : diffFiltersObj.newResultsFilters,
      resolvedResultsFilters   : diffFiltersObj.resolvedResultsFilters,
      unresolvedResultsFilters : diffFiltersObj.unresolvedResultsFilters,
      defaultSort              : that._getDefaultSortOptions(),
      total                    : count,
    };

    return query;
  },


  /**
   * Transforms a filter array from a Run view given by the Filter widgets to
   * the correct Thrift Api format.
   *
   * @param filterObjArray An array of the filter objects from all the Filter
   * Widgets.
   * @return The Thrift API compatible filter array.
   */
  _createRunApiFilters : function (filterObjArray) {
    var that = this;

    var filters = [];

    filterObjArray.forEach(function (item) {
      var filter = new codeCheckerDBAccess.ReportFilter();

      filter.filepath = item.pathState === "" ? "*" : item.pathState;

      switch (item.supprState) {
        case "supp"  : filter.suppressed = true; break;
        case "unsupp": filter.suppressed = false; break;
      }

      var itemCheckerInfo = item.checkerInfoState.split("##");

      switch (itemCheckerInfo[0]) {
        case "severity":
          filter.severity = parseInt(itemCheckerInfo[1]);
          break;
        case "checker":
          filter.checkerId = itemCheckerInfo[1];
          break;
        case "all": // Do nothing
          break;
      }

      filters.push(filter);
    });

    return filters;
  },


  /**
   * Transforms a filter array from a Diff view given by the Filter widgets to
   * the correct Thrift API format.
   *
   * @param filterObjArray An array of the filter objects in all the Filter
   * Widgets
   * @param The three Thript API compatible Diff filters in an object.
   */
  _createDiffApiFilters : function (filterObjArray) {
    var that = this;

    var newResultsFilters        = [];
    var resolvedResultsFilters   = [];
    var unresolvedResultsFilters = [];

    filterObjArray.forEach(function (item) {
      var filter = new codeCheckerDBAccess.ReportFilter();

      filter.filepath = item.pathState === "" ? "*" : item.pathState;

      switch (item.supprState) {
        case "supp"  : filter.suppressed = true; break;
        case "unsupp": filter.suppressed = false; break;
      }

      var itemCheckerInfo = item.checkerInfoState.split("##");
      switch (itemCheckerInfo[0]) {
        case "severity": filter.severity = parseInt(itemCheckerInfo[1]); break;
        case "checker" : filter.checkerId = itemCheckerInfo[1]; break;
        case "all"     : /* Do nothing */ break;
      }

      switch (item.resolvState) {
        case "newonly" : newResultsFilters.push(filter); break;
        case "resolv"  : resolvedResultsFilters.push(filter); break;
        case "unresolv": unresolvedResultsFilters.push(filter); break;
      }
    });

    return {
      newResultsFilters        : newResultsFilters,
      resolvedResultsFilters   : resolvedResultsFilters,
      unresolvedResultsFilters : unresolvedResultsFilters,
    };
  },


  /**
   * Refreshes the title of the Run Overview to show the correct count of hits
   * found in the database.
   */
  _refreshRunHitCount : function (count) {
    var that = this;

    that.myOverviewTC.overviewBC.set('title', 'Run Overview - hits : ' + count);
  },


  /**
   * Refreshes the title of the Diff Overview to show the correct count of hits
   * found in the database.
   */
  _refreshDiffHitCount : function (count) {
    var that = this;

    that.myOverviewTC.overviewBC.set('title', 'Diff Overview - hits : ' + count);
  },


  /**
   * Refreshes (reloads) the overview grid by creating a new query
   * (in dojo/data API format) according to the current filters and state.
   * It also calls the correct hit count refreshing function.
   */
  refreshGrid : function () {
    var that = this;

    var query;
    var countDef = new Deferred();
    var filterObjArray = that.myOverviewTC.getStateOfFilters();

    if (that.myOverviewTC.overviewType === "run") {

      var filters = that._createRunApiFilters(filterObjArray);

      that.getCount(
        that.myOverviewTC.overviewType,
        [that.myOverviewTC.runId],
        { filters : filters },
        function (count) {
          if (count instanceof RequestFailed) {
            countDef.reject("Failed to get hit count for Run");
          } else {
            countDef.resolve(count);
            that._refreshRunHitCount(count);
          }
        }
      );

      query = that._createRunOverviewQuery(filters, countDef);

    } else if (that.myOverviewTC.overviewType === "diff") {

      var filtersObj = that._createDiffApiFilters(filterObjArray);

      that.getCount(
        that.myOverviewTC.overviewType,
        [that.myOverviewTC.runId1, that.myOverviewTC.runId2],
        filtersObj,
        function (count) {
          if (count instanceof RequestFailed) {
            countDef.reject("Failed to get hit count for Diff");
          } else {
            countDef.resolve(count);
            that._refreshDiffHitCount(count);
          }
        }
      );

      query = that._createDiffOverviewQuery(filtersObj, countDef);

    }

    that.setQuery(query, query);
  },


  /**
   * Gets the hit count for a Run or a Diff.
   *
   * @param overviewType Type of the Overview.
   * @param runIds An array consisting of one (Run) or two (Diff) runIds.
   * @param filterObj An object containing one (Run) or three (Diff) filter arrays.
   * @param callback Callback function to call after the query/queries finish.
   *
   */
  getCount : function (overviewType, runIds, filterObj, callback) {

    if (overviewType === "run") {

      CC_SERVICE.getRunResultCount(
        runIds[0],
        filterObj.filters,
        function (count) {
          if (count instanceof RequestFailed) {
            console.log("Thrift API call 'getRunResultCount' failed!");
          }

          callback(count);
        }
      );

    } else if (overviewType === "diff") {

      var newCount           = null;
      var resolvedCount      = null;
      var unresolvedCount    = null;
      var finishedQueryCount = 0;

      var finishedCountQueries = function (error) {
        if (newCount !== null && resolvedCount !== null && unresolvedCount !== null) {
          callback(newCount + resolvedCount + unresolvedCount);
        } else if (finishedQueryCount === 3) {
          callback(error);
        }
      };

      if (filterObj.newResultsFilters.length > 0) {
        CC_SERVICE.getDiffResultCount(
          runIds[0],
          runIds[1],
          codeCheckerDBAccess.DiffType.NEW,
          filterObj.newResultsFilters,
          function (count) {
            if (count instanceof RequestFailed) {
              error = true;
              console.log("Thrift API call 'getDiffResultCount' failed!");
            } else {
              newCount = count;
            }

            finishedQueryCount += 1;
            finishedCountQueries(count);
          }
        );
      } else {
        newCount = 0;
        finishedQueryCount += 1;
      }

      if (filterObj.resolvedResultsFilters.length > 0) {
        CC_SERVICE.getDiffResultCount(
          runIds[0],
          runIds[1],
          codeCheckerDBAccess.DiffType.RESOLVED,
          filterObj.resolvedResultsFilters,
          function (count) {
            if (count instanceof RequestFailed) {
              error = true;
              console.log("Thrift API call 'getDiffResultCount' failed!");
            } else {
              resolvedCount = count;
            }

            finishedQueryCount += 1;
            finishedCountQueries(count);
          }
        );
      } else {
        resolvedCount = 0;
        finishedQueryCount += 1;
      }

      if (filterObj.unresolvedResultsFilters.length > 0) {
        CC_SERVICE.getDiffResultCount(
          runIds[0],
          runIds[1],
          codeCheckerDBAccess.DiffType.UNRESOLVED,
          filterObj.unresolvedResultsFilters,
          function (count) {
            if (count instanceof RequestFailed) {
              console.log("Thrift API call 'getDiffResultCount' failed!");
            } else {
              unresolvedCount = count;
            }

            finishedQueryCount += 1;
            finishedCountQueries(count);
          }
        );
      } else {
        unresolvedCount = 0;
        finishedQueryCount += 1;
      }

    }
  },


});});
