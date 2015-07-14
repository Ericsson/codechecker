// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dijit/layout/BorderContainer",
  "dijit/layout/TabContainer",
  "dijit/layout/ContentPane",
  "dijit/Dialog",
  "scripts/codecheckerviewer/OverviewGrid.js",
  "scripts/codecheckerviewer/OverviewHeader.js",
  "scripts/codecheckerviewer/FileViewBC.js",
  "scripts/codecheckerviewer/widgets/Pager.js",
], function ( declare, BorderContainer, TabContainer, ContentPane, Dialog
            , OverviewGrid, OverviewHeader, FileViewBC, Pager ) {
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


    that.overviewBC = new BorderContainer();

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

        that.openFileView( that.overviewGrid.getItem(evt.rowIndex).fileId[0]
                         , that.overviewGrid.getItem(evt.rowIndex).checkedFile[0]
                         , that.overviewGrid.getItem(evt.rowIndex).bugHash[0]
                         , that.overviewGrid.getItem(evt.rowIndex).severity[0]
                         , that.overviewGrid.getItem(evt.rowIndex).lastBugPosition[0]
                         , that.overviewGrid.getItem(evt.rowIndex).reportId[0]
                         , that.overviewGrid.getItem(evt.rowIndex).checkerId[0]
                         , that.overviewGrid.getItem(evt.rowIndex).suppressed[0]
                         , that.overviewGrid.getItem(evt.rowIndex).runId[0]
                         , that.overviewType
                         );

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
  },


  showDocumentation : function(checkerId) {
    var checkerDocDialog = new Dialog({
      title   : "Documentation for <b>" + checkerId + "</b>",
      content : marked(CC_SERVICE.getCheckerDoc(checkerId))
    });

    checkerDocDialog.show();
  },


  openFileView : function( fileId, checkedFile, bugHash, severity, lastBugPosition
                        , reportId, currCheckerId, suppressed, runId, overviewType) {
    var that = this;


    var newFileViewBC = new FileViewBC({
      fileId          : fileId,
      checkedFile     : checkedFile,
      bugHash         : bugHash,
      severity        : severity,
      lastBugPosition : lastBugPosition,
      reportId        : reportId,
      myOverviewTC    : that,
      currCheckerId   : currCheckerId,
      suppressed      : suppressed,
      runId           : runId,
      overviewType    : overviewType
    });

    that.addChild(newFileViewBC);

    that.selectChild(newFileViewBC);
  },


  getStateOfFilters : function() {
    var that = this;

    return that.overviewHeader.getStateOfFilters();
  }


});});
