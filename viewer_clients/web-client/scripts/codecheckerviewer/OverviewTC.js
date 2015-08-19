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
  "scripts/codecheckerviewer/FileViewBC.js",
  "scripts/codecheckerviewer/widgets/Pager.js",
], function ( declare, hash, topic, ioQuery, BorderContainer, TabContainer
            , ContentPane, Dialog, OverviewGrid, OverviewHeader, FileViewBC
            , Pager ) {
return declare(TabContainer, {

  // overviewType ("run" or "diff")
  // if "run" : runId
  // if "diff": runId1, runId2


  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);
  },

  postCreate : function () {
    var that = this;
    that.inherited(arguments);

    that.overviewBC = new BorderContainer({
      id     : that.id + '_overview',
      onShow : function() {
        that.openFileView(undefined, undefined);
      }
    });

    that.overviewGridCP = new ContentPane({
      region : "center",
      style  : "margin: 0px; padding: 0px;"
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

        that.showDocumentation(that.overviewGrid.getItem(evt.rowIndex).checkerId[0]);

      } else if (evt.cell.field === "fileWithBugPos") {
        var row = that.overviewGrid.getItem(evt.rowIndex);
        that.openFileView(row.reportId[0], row.runId[0]);
      }
    };


    that.overviewHeader = new OverviewHeader({
      overviewType   : that.overviewType,
      myOverviewTC   : that,
      region         : "top",
      style          : "background-color: white; margin: 0px; padding: 0px;"
    });


    if (that.overviewType === "run") {
      that.overviewPagerCP = new ContentPane({
        region : "bottom",
        style  : "margin: 0px; padding: 0px;"
      });


      that.overviewPager = new Pager({
        myOverviewTC : that,
        style        : "text-align: right"
      });

      that.overviewPagerCP.addChild(that.overviewPager);
      that.overviewBC.addChild(that.overviewPagerCP);
    }


    that.overviewGridCP.addChild(that.overviewGrid);
    that.overviewBC.addChild(that.overviewGridCP);
    that.overviewBC.addChild(that.overviewHeader);

    that.addChild(that.overviewBC);

    topic.subscribe("/dojo/hashchange", function(changedHash) {
      that.handleHashChange(changedHash);
    });

    // Restore previous state from cuttent hash (if any).
    that.handleHashChange(hash());
  },

  handleHashChange : function(changedHash) {
    if (!changedHash) {
      return;
    }

    var that = this;
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
      if (row.reportId[0] == hashState.fvReportId) {
        break;
      }
      rowIndex++;
    }

    if (row) {
      var reportData = {
        checkerId       : row.checkerId[0],
        bugHash         : row.bugHash[0],
        checkedFile     : row.checkedFile[0],
        checkerMsg      : '',
        reportId        : row.reportId[0],
        suppressed      : row.suppressed[0],
        fileId          : row.fileId[0],
        lastBugPosition : row.lastBugPosition[0],
        severity        : row.severity[0],
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

        that.handleOpenFileView(reportData, parseInt(hashState.fvRunId), tabId);
        hash(changedHash);
      });
    }
  },

  showDocumentation : function(checkerId) {
    var checkerDocDialog = new Dialog({
      title   : "Documentation for <b>" + checkerId + "</b>",
      content : marked(CC_SERVICE.getCheckerDoc(checkerId))
    });

    checkerDocDialog.show();
  },

  getFileViewId : function(hashState) {
    var that = this;

    if (hashState.fvReportId && hashState.fvRunId) {
      return that.id + "_" + hashState.fvReportId + "_" + hashState.fvRunId;
    }

    return that.id + "_overview";
  },

  openFileView : function(reportId, runId) {
    var that = this;
    var hashState = ioQuery.queryToObject(hash());
    hashState.fvReportId = reportId;
    hashState.fvRunId = runId;
    hash(ioQuery.objectToQuery(hashState));
  },

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


  getStateOfFilters : function() {
    var that = this;

    return that.overviewHeader.getStateOfFilters();
  }


});});
