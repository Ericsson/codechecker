// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/data/ObjectStore",
  "dojox/grid/DataGrid",
  "scripts/codecheckerviewer/OverviewStore.js",
], function ( declare, ObjectStore, DataGrid, OverviewStore ) {
return declare(DataGrid, {


  /**
   * Construct the new object. The following arguments are required:
   *   myOverviewTC: The OverviewTC this object belongs to
   */
  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);

    that.ovStore   = new OverviewStore({});
    that.store     = new ObjectStore({objectStore: that.ovStore});
    that.cellWidth = ((100)/5).toString() + "%";

    that.structure = [
      { name: "File", field: "fileWithBugPos", styles: "text-align: center;", width: that.cellWidth , formatter: function(data) { return data.split('\n').join('<br/>'); } },
      { name: "Message", field: "checkerMsg", styles: "text-align: center;", width: that.cellWidth },
      { name: "Checker name", field: "checkerId", styles: "text-align: center;", width: that.cellWidth },
      { name: "Severity", field: "severity", styles: "text-align: center;", width: that.cellWidth },
      { name: "Suppress Comment", field: "suppressComment", styles: "text-align: center;", width: that.cellWidth },
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
  canSort : function(inSortInfo) {
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
  _getDefaultSortOptions : function() {
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
   * @return a new query object.
   */
  _createRunOverviewQuery : function(runFilters) {
    var that = this;
    var query = {
      overviewType : "run",
      runId        : that.myOverviewTC.runId,
      filters      : runFilters,
      defaultSort  : that._getDefaultSortOptions()
    };

    return query;
  },


  /**
   * Creates a new Diff view query object using the given filter settings. This
   * is a helper method for _createQuery.
   *
   * @param diffFiltersObj The three Diff filter arrays in an object
   * (see OverviewGrid::_createDiffApiFilters)
   * @return a new query object.
   */
  _createDiffOverviewQuery : function(diffFiltersObj) {
    var that = this;

    var query = {
      overviewType             : "diff",
      runId1                   : that.myOverviewTC.runId1,
      runId2                   : that.myOverviewTC.runId2,
      newResultsFilters        : diffFiltersObj.newResultsFilters,
      resolvedResultsFilters   : diffFiltersObj.resolvedResultsFilters,
      unresolvedResultsFilters : diffFiltersObj.unresolvedResultsFilters,
      defaultSort              : that._getDefaultSortOptions()
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
  _createRunApiFilters : function(filterObjArray) {
    var that = this;

    var filters = [];

    filterObjArray.forEach(function(item) {
      var filter = new codeCheckerDBAccess.ReportFilter();

      filter.filepath = item.pathState === "" ? "*" : item.pathState;

      switch (item.supprState) {
        case "supp":
          filter.suppressed = true;
          break;
        case "unsupp":
          filter.suppressed = false;
          break;
        case "all": // Do nothing
          break;
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
    })

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
  _createDiffApiFilters : function(filterObjArray) {
    var that = this;

    var newResultsFilters        = [];
    var resolvedResultsFilters   = [];
    var unresolvedResultsFilters = [];

    filterObjArray.forEach(function(item) {
      var filter = new codeCheckerDBAccess.ReportFilter();

      filter.checkerId = item.checkerTypeState;

      filter.filepath = item.pathState === "" ? "*" : item.pathState;

      if (item.severityState !== "all") {
         filter.severity = parseInt(item.severityState);
      }

      switch (item.supprState) {
        case "supp"  : filter.suppressed = true;
          break;
        case "unsupp": filter.suppressed = false;
          break;
        case "all"   : /*DO NOTHING*/
          break;
      }

      switch (item.resolvState) {
        case "newonly" : newResultsFilters.push(filter);
          break;
        case "resolv"  : resolvedResultsFilters.push(filter);
          break;
        case "unresolv": unresolvedResultsFilters.push(filter);
          break;
      }
    })

    return {
      newResultsFilters        : newResultsFilters,
      resolvedResultsFilters   : resolvedResultsFilters,
      unresolvedResultsFilters : unresolvedResultsFilters
    };
  },


  /**
   * Refreshes the title of the Run Overview to show the correct count of hits
   * found in the database.
   *
   * @param runFilters The current (Thrift Api compatible)filters of the Run.
   */
  _refreshRunHitCount : function(runFilters) {
    var that = this;

    CC_SERVICE.getRunResultCount(
      that.myOverviewTC.runId,
      runFilters,
      function(result) {
        that.myOverviewTC.overviewBC.set('title', 'Run Overview - hits : ' + result);
      });
  },


  /**
   * Refreshes the title of the Diff Overview to show the correct count of hits
   * found in the database.
   *
   * @param diffFiltersObj The current three (Thrift Api compatible)filter
   * arrays of the Diff in an object.
   */
  _refreshDiffHitCount : function(diffFiltersObj) {
    // Not supported yet.
  },


  /**
   * Refreshes (reloads) the overview grid by creating a new query
   * (in dojo/data API format) according to the current filters and state.
   * It also calls the correct hit count refreshing function.
   */
  refreshGrid : function() {
    var that = this;

    var query;
    var filterObjArray = that.myOverviewTC.getStateOfFilters();

    if (that.myOverviewTC.overviewType === "run") {
      var filters = that._createRunApiFilters(filterObjArray);
      that._refreshRunHitCount(filters);
      query = that._createRunOverviewQuery(filters);
    } else if (that.myOverviewTC.overviewType === "diff") {
      var filtersArray = that._createDiffApiFilters(filterObjArray);
      // TODO: Diff hit count refreshing function should be called here.
      query = that._createDiffOverviewQuery(filtersArray);
    }

    that.setQuery(query, query);
  }


});});
