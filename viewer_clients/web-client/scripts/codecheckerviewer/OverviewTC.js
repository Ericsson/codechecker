// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/hash",
  "dojo/topic",
  "dojo/io-query",
  "dijit/layout/BorderContainer",
  "dijit/layout/TabContainer",
  "dijit/layout/ContentPane",
  "dijit/Dialog",
  "scripts/codecheckerviewer/OverviewGrid.js",
  "scripts/codecheckerviewer/OverviewHeader.js",
  "scripts/codecheckerviewer/FileViewBC.js"
], function ( declare, hash, topic, ioQuery, BorderContainer, TabContainer
            , ContentPane, Dialog, OverviewGrid, OverviewHeader, FileViewBC ) {
return declare(TabContainer, {


   /**
   * Construct the new object. The following arguments are required:
   *   overviewType: "run" or "diff"
   *
   *   Other parameters depending on overviewType:
   *     if overviewType is "run":
   *       runId: the runId of the run
   *     if overviewType is "diff":
   *       runId1: the runId of the baseline run
   *       runId2: the runId of the new run
   */
  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);
  },


  /**
   * Build the layout, add event listeners, build the dom for the widget
   */
  postCreate : function () {
    var that = this;
    that.inherited(arguments);

    that.overviewBC = new BorderContainer({
      id     : that.id + '_overview',
      style  : "margin: 5px; padding: 0px;",
      onShow : function() {
        that.openFileView(undefined, undefined);
      }
    });

    that.overviewGridCP = new ContentPane({
      region : "center",
      style  : "margin: 0px; padding: 0px;"
    });

    that.overviewHeader = new OverviewHeader({
      overviewType   : that.overviewType,
      myOverviewTC   : that,
      region         : "top",
      style          : "background-color: white; margin: 0px; padding: 0px;"
    });

    that.overviewGrid = null;
    if (that.overviewType === "run") {

      that.overviewBC.title = "Run Overview";

      that.overviewGrid = new OverviewGrid({
        myOverviewTC  : that,
        runId         : that.runId,
        region        : "center",
        id            : "runoverviewgrid_" + that.runId,
        class         : "overviewGrid",
        selectionMode : "none",
        style         : "border: 0px; margin: 0px; padding: 0px;"
      });

    } else if (that.overviewType === "diff") {

      that.overviewBC.title = "Diff Overview";

      that.overviewGrid = new OverviewGrid({
        myOverviewTC  : that,
        runId1        : that.runId1,
        runId2        : that.runId2,
        region        : "center",
        id            : "diffoverviewgrid_" + that.runId1 + "_" + that.runId2,
        class         : "overviewGrid",
        selectionMode : "none",
        style         : "border: 0px; margin: 0px; padding: 0px;"
      });

    }

    that.overviewGrid.onRowClick = function (evt) {
      if (evt.cell.field === "checkerId") {
        that.showDocumentation(that.overviewGrid.getItem(evt.rowIndex).checkerId);
      } else if (evt.cell.field === "fileWithBugPos") {
        var row = that.overviewGrid.getItem(evt.rowIndex);
        that.openFileView(row.reportId, row.runId);
      }
    };

    that.overviewGridCP.addChild(that.overviewGrid);
    that.overviewBC.addChild(that.overviewGridCP);
    that.overviewBC.addChild(that.overviewHeader);

    that.addChild(that.overviewBC);

    that.hashchangeHandle = topic.subscribe("/dojo/hashchange", function(changedHash) {
      that.handleHashChange(changedHash);
    });

    // Restore previous state from cuttent hash (if any).
    that.handleHashChange(hash());
  },


  /**
   * Handles a hash change.
   *
   * @param {String} changedHash the changed browser hash.
   */
  handleHashChange : function(changedHash) {
    var that = this;

    if (!changedHash) {
      return;
    }

    var hashState = ioQuery.queryToObject(changedHash);
    var ovId = CC_UTIL.getOverviewIdFromHashState(hashState);
    if (!hashState || ovId != that.id) {
      return;
    }

    var tabId = that.getFileViewId(hashState);
    if (undefined !== dijit.byId(tabId)) {
      that.selectChild(dijit.byId(tabId));
      return;
    }

    // Maybe it's in the GRID. Use it as a cache.
    var rowIndex = 0;
    var row;
    while ((row = that.overviewGrid.getItem(rowIndex)))
    {
      if (row.reportId == hashState.fvReportId) {
        break;
      }
      rowIndex++;
    }

    if (row) {
      var reportData = {
        checkerId       : row.checkerId,
        bugHash         : row.bugHash,
        checkedFile     : row.checkedFile,
        checkerMsg      : '',
        reportId        : row.reportId,
        suppressed      : row.suppressed,
        fileId          : row.fileId,
        lastBugPosition : row.lastBugPosition,
        severity        : row.severity,
        moduleName      : '',
        suppressComment : ''
      }

      that.handleOpenFileView(reportData, parseInt(hashState.fvRunId), tabId);
    } else {
      // Need to query
      CC_SERVICE.getReport(parseInt(hashState.fvReportId), function(reportData){
        if (typeof reportData === "string") {
          console.error("getReport failed: " + reportData);
          return;
        }

        reportData.severity = CC_UTIL.severityFromCodeToString(
          reportData.severity);
        that.handleOpenFileView(reportData, parseInt(hashState.fvRunId), tabId);
        hash(changedHash);
      });
    }
  },


  /**
   * Show the documentation of the given checker.
   *
   * @param checkerId checker id.
   */
  showDocumentation : function(checkerId) {
    CC_SERVICE.getCheckerDoc(checkerId, function(checkerDoc) {
      var checkerDocDialog = new Dialog({
        title   : "Documentation for <b>" + checkerId + "</b>",
        content : marked(checkerDoc)
      });

      checkerDocDialog.show();
    });
  },


  /**
   * Returns the DOM id string of a tab using the given browser has state
   * object.
   *
   * @param hashState hash state
   */
  getFileViewId : function(hashState) {
    var that = this;

    if (hashState.fvReportId && hashState.fvRunId) {
      return that.id + "_" + hashState.fvReportId + "_" + hashState.fvRunId;
    }

    return that.id + "_overview";
  },


  /**
   * Opens a new file view using the browser hash. See handleOpenFileView for
   * implementation.
   *
   * @param reportId a report id
   * @param runId run id for the report
   */
  openFileView : function(reportId, runId) {
    var that = this;

    var hashState = ioQuery.queryToObject(hash());
    hashState.fvReportId = reportId;
    hashState.fvRunId = runId;
    hash(ioQuery.objectToQuery(hashState));
  },


  /**
   * Handles a request for opening a new file overview.
   *
   * @param reportData a ReportData.
   * @param runId run id
   * @param tabId DOM id for the new tab
   */
  handleOpenFileView : function(reportData, runId, tabId) {
    var that = this;
    var newFileViewBC = new FileViewBC({
      id              : tabId,
      fileId          : reportData.fileId,
      checkedFile     : reportData.checkedFile,
      bugHash         : reportData.bugHash,
      severity        : reportData.severity,
      lastBugPosition : reportData.lastBugPosition,
      reportId        : reportData.reportId,
      myOverviewTC    : that,
      currCheckerId   : reportData.checkerId,
      suppressed      : reportData.suppressed,
      runId           : runId,
      onShow          : function() {
        that.openFileView(reportData.reportId, runId);
      }
    });

    that.addChild(newFileViewBC);
    that.selectChild(newFileViewBC);
  },


  /**
   * Returns the state of filters (see OverviewHeader::getStateOfFilters).
   */
  getStateOfFilters : function() {
    var that = this;

    return that.overviewHeader.getStateOfFilters();
  }

});});
