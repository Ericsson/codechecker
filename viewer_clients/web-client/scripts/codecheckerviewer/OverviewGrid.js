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

    that.ovStore = new OverviewStore({});
    that.store = new ObjectStore({objectStore: that.ovStore});
    that.cellWidth = ((100)/5).toString() + "%";

    that.structure = [
      { name: "Index", field: "reportId", styles: "text-align: center;", width: "40px" },
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

    that.query = that._createQuery();
    that.queryOptions = that.query;
  },


  /**
   * Returns whether sorting is allowed or not for the given cell.
   *
   * For parameters see dojox/grid/DataGrid documentation.
   */
  canSort: function(inSortInfo) {
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
  _getDefaultSortOptions: function() {
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
   * Creates a new runoverbiew query object using the given filter settings.
   * This is a helper method for _createQuery.
   *
   * @param filterObjArray filters (see OverviewTC::getStateOfFilters)
   * @return a new query object.
   */
  _createRunOverviewQuery: function(filterObjArray) {
    var that = this;
    var query = {
      overviewType  : "run",
      runId         : that.myOverviewTC.runId,
      filters       : [],
      defaultSort   : that._getDefaultSortOptions()
    };

    for (var i = 0 ; i < filterObjArray.length ; ++i) {
      var filter = new codeCheckerDBAccess.ReportFilter();

      filter.checkerId = filterObjArray[i].checkerTypeState;

      var filepathTmp = filterObjArray[i].pathState;
      filter.filepath = filepathTmp === "" ? "*" : filepathTmp;

      var severityTmp = filterObjArray[i].severityState;
      if (severityTmp !== "all") {
         filter.severity = parseInt(severityTmp);
      }

      switch (filterObjArray[i].supprState) {
        case "supp":
          filter.suppressed = true;
          break;
        case "unsupp":
          filter.suppressed = false;
          break;
        case "all":
          // DO NOTHING
          break;
      }

      query.filters.push(filter);
    }

    return query;
  },


  /**
   * Creates a new diff view query object using the given filter settings. This
   * is a helper method for _createQuery.
   *
   * @param filterObjArray filters (see OverviewTC::getStateOfFilters)
   * @return a new query object.
   */
  _createDiffOverviewQuery: function(filterObjArray) {
    var that = this;
    var query = {
      overviewType              : "diff",
      runId1                    : that.myOverviewTC.runId1,
      runId2                    : that.myOverviewTC.runId2,
      newResultsFilters         : [],
      resolvedResultsFilters    : [],
      unresolvedResultsFilters  : [],
      defaultSort               : that._getDefaultSortOptions()
    };

    for (var i = 0 ; i < filterObjArray.length ; ++i) {
      var filter = new codeCheckerDBAccess.ReportFilter();

      filter.checkerId = filterObjArray[i].checkerTypeState;

      var filepathTmp = filterObjArray[i].pathState;
      filter.filepath = filepathTmp === "" ? "*" : filepathTmp;

      var severityTmp = filterObjArray[i].severityState;
      if (severityTmp !== "all") {
         filter.severity = parseInt(severityTmp);
      }

      switch (filterObjArray[i].supprState) {
        case "supp":
          filter.suppressed = true;
          break;
        case "unsupp":
          filter.suppressed = false;
          break;
        case "all":
          // DO NOTHING
          break;
      }

      switch (filterObjArray[i].resolvState) {
        case "newonly":
          query.newResultsFilters.push(filter);
          break;
        case "resolv":
          query.resolvedResultsFilters.push(filter);
          break;
        case "unresolv":
          query.unresolvedResultsFilters.push(filter);
          break;
      }
    }

    return query;
  },


  /**
   * Creates a new query (in dojo/data API format) according to the current
   * filters and state.
   *
   * @return a new state objects.
   */
  _createQuery : function() {
    var that = this;

    var filterObjArray = that.myOverviewTC.getStateOfFilters();
    var query;
    if (that.myOverviewTC.overviewType === "run") {
      query = that._createRunOverviewQuery(filterObjArray);
    } else if (that.myOverviewTC.overviewType === "diff") {
      query = that._createDiffOverviewQuery(filterObjArray);
    }

    return query;
  },


  /**
   * Refreshes (reloads) the overview grid using the current filter settings.
   */
  refreshGrid : function() {
    var that = this;
    var query = that._createQuery();

    that.setQuery(query, query);

    // that.render();
  }

});});
