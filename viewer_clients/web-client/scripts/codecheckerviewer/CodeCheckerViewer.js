// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dijit/Dialog",
  "dijit/layout/BorderContainer",
  "dijit/layout/TabContainer",
  "dijit/layout/ContentPane",
  "dijit/form/Button",
  "scripts/codecheckerviewer/ListOfRunsGrid.js",
  "scripts/codecheckerviewer/OverviewTC.js",
  "scripts/codecheckerviewer/Util.js",
  "scripts/codecheckerviewer/widgets/DiffWidget.js",
  "scripts/codecheckerviewer/widgets/MenuButton.js",
], function ( declare, Dialog, BorderContainer, TabContainer, ContentPane
            , Button, ListOfRunsGrid, OverviewTC, Util, DiffWidget
            , MenuButton ) {
return declare(null, {


  constructor : function() {
    var that = this;


    that.checkedRunIds = [];
    that.checkedNames  = [];


    that.initGlobals();

    that.buildLayout();

    that.buildListOfRuns();

    that.buildMenuButton();

    that.layout.startup();

    that.listOfRunsGrid.fillGridWithRunData();

    that.listOfRunsGrid.render();

  },


  initGlobals : function() {
    CC_SERVICE = new codeCheckerDBAccess.codeCheckerDBAccessClient(new Thrift.Protocol(new Thrift.Transport("CodeCheckerService")));
    CC_UTIL    = new Util();
  },


  buildLayout : function() {
    var that = this;


    that.layout = new BorderContainer({
      id    : "layout",
      style : "height: 100%;",
    });

    that.headerPane = new ContentPane({
      id     : "headerpane",
      region : "top",
      class  : "headerPane"
    });

    that.mainTC = new TabContainer({
      id     : "mainTC",
      region : "center",
      style  : "padding:0px;"
    });


    that.layout.addChild(that.headerPane);
    that.layout.addChild(that.mainTC);

    document.body.appendChild(that.layout.domNode);
  },


  buildListOfRuns : function() {
    var that = this;


    that.listOfRunsGridCP = new ContentPane({
      region : "center",
      style  : "margin: 0px; padding: 0px;"
    });


    that.listOfRunsGrid = new ListOfRunsGrid({
      region        : "center",
      id            : "listofrunsgrid",
      class         : "listOfRunsGrid",
      title         : "List of runs",
      selectionMode : "none",
      style         : "font-family: 'Ubuntu', sans-serif; padding: 0px; margin: 0px; border: 0px;",
      onRowClick    : function(evt) {

        switch (evt.cell.field) {

          case "name":

            var tempRunId = that.listOfRunsGrid.getItem(evt.rowIndex).runid[0];
            var tempName = that.listOfRunsGrid.getItem(evt.rowIndex).name[0];
            var tempNumberOfBugs = that.listOfRunsGrid.getItem(evt.rowIndex).numberofbugs[0];
            that.newRunOverviewTab(tempRunId, tempName, tempNumberOfBugs);

            break;

          case "diffDisplay":

            var tempDiff = that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0];
            var tempNumberOfBugs = that.listOfRunsGrid.getItem(evt.rowIndex).name[0];

            var checkedNumber = that.listOfRunsGrid.getCheckedNumber();

            if (tempDiff) {

              that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0] = false;
              that.listOfRunsGrid.getItem(evt.rowIndex).diffDisplay[0] = false;
              that.listOfRunsGrid.update();

              for(var i = 0 ; i < checkedNumber ; ++i) {
                if(that.checkedRunIds[i] === that.listOfRunsGrid.getItem(evt.rowIndex).runid[0]) {
                  that.checkedRunIds.splice(i, 1);
                }
                if(that.checkedNames[i] === that.listOfRunsGrid.getItem(evt.rowIndex).name[0]) {
                  that.checkedNames.splice(i, 1);
                }
              }

            } else {

              if (checkedNumber < 2) {
                that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0] = true;
                that.listOfRunsGrid.getItem(evt.rowIndex).diffDisplay[0] = true;
                that.listOfRunsGrid.update();

                that.checkedRunIds.push(that.listOfRunsGrid.getItem(evt.rowIndex).runid[0]);
                that.checkedNames.push(that.listOfRunsGrid.getItem(evt.rowIndex).name[0]);
              } else {
                that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0] = false;
                that.listOfRunsGrid.getItem(evt.rowIndex).diffDisplay[0] = false;
                that.listOfRunsGrid.update();
              }

            }

            checkedNumber = that.listOfRunsGrid.getCheckedNumber();

            if (checkedNumber === 2) {
              that.diffWidget.setButtonDisabled(false);
            } else {
              that.diffWidget.setButtonDisabled(true);
            }


            if (checkedNumber === 0) {
              that.diffWidget.setDiffLabel("-", "-");
            } else if (checkedNumber === 1) {
              that.diffWidget.setDiffLabel(that.checkedRunIds[0], "-");
            } else {
              that.diffWidget.setDiffLabel(that.checkedRunIds[0], that.checkedRunIds[1]);
            }

            break;

        }


      }
    });


    that.diffWidget = new DiffWidget();


    that.listOfRunsBC = new BorderContainer({
      id    : "bc_listofrunsgrid",
      title : that.listOfRunsGrid.title
    });


    that.listOfRunsGridCP = new ContentPane({
      region : "center",
      style  : "margin: 0px; padding: 0px;"
    });

    that.diffWidgetCP = new ContentPane({
      region : "bottom",
      style  : "margin: 0px; padding: 0px;"
    });


    that.listOfRunsGridCP.addChild(that.listOfRunsGrid);
    that.diffWidgetCP.addChild(that.diffWidget);

    that.listOfRunsBC.addChild(that.listOfRunsGridCP);
    that.listOfRunsBC.addChild(that.diffWidgetCP);

    that.mainTC.addChild(that.listOfRunsBC);

  },


  buildMenuButton : function() {
    var that = this;


    var menuButton = new MenuButton({
      mainTC : that.mainTC,
    });

    that.headerPane.addChild(menuButton);
  },


  newRunOverviewTab : function(runId, name, numberOfBugs) {
    var that = this;


    var idOfNewOverviewTC = "runoverviewtc_" + runId;

    if (undefined !== dijit.byId(idOfNewOverviewTC)) {
      that.mainTC.selectChild(dijit.byId(idOfNewOverviewTC));

      return;
    }

    var newOverviewTC = new OverviewTC({
      id           : idOfNewOverviewTC,
      runId        : runId,
      overviewType : "run",
      title        : name,
      closable     : true,
      style        : "padding: 5px;",
      onClose      : function() {
        if (that.mainTC.selectedChildWidget === newOverviewTC) {
          that.mainTC.selectChild("bc_listofrunsgrid");
        }

        return true;
      }
    });

    try {

      newOverviewTC.overviewGrid.fillOverviewGrid(newOverviewTC.getStateOfFilters(),
        newOverviewTC.overviewPager.getPagerParams());

      newOverviewTC.overviewPager.disableArrowsAsNeeded();

      that.mainTC.addChild(newOverviewTC);
      that.mainTC.selectChild(newOverviewTC);

      newOverviewTC.overviewGrid.render();

    } catch (err) {

      newOverviewTC.destroyRecursive();
      console.log(err);

    }

  },


  newDiffOverviewTab : function(runId1, runId2, name1, name2) {
    var that = this;


    var idOfNewOverviewTC = "diffoverviewtc_" + runId1 + "_" + runId2;

    if (undefined !== dijit.byId(idOfNewOverviewTC)) {
      that.mainTC.selectChild(dijit.byId(idOfNewOverviewTC));

      return;
    }

    var newOverviewTC = new OverviewTC({
      id           : idOfNewOverviewTC,
      runId1       : runId1,
      runId2       : runId2,
      overviewType : "diff",
      title        : "Diff of " + name1 + " and " + name2,
      closable     : true,
      style        : "padding: 5px;",
      onClose      : function() {
        if (that.mainTC.selectedChildWidget === newOverviewTC) {
          that.mainTC.selectChild("bc_listofrunsgrid");
        }

        return true;
      }
    });

    try {

      newOverviewTC.overviewGrid.fillOverviewGrid(newOverviewTC.getStateOfFilters());

      // newOverviewTC.overviewGrid.fillOverviewGrid(newOverviewTC.getStateOfFilters(),
      //   newOverviewTC.overviewPager.getPagerParams());
      // newOverviewTC.overviewPager.disableArrowsAsNeeded();

      that.mainTC.addChild(newOverviewTC);
      that.mainTC.selectChild(newOverviewTC);

      newOverviewTC.overviewGrid.render();

    } catch (err) {

      newOverviewTC.destroyRecursive();
      console.log(err);

    }

  },


  reset : function() {
    var that = this;


    that.listOfRunsGrid.recreateStore();
    that.listOfRunsGrid.fillGridWithRunData()
    that.listOfRunsGrid.render();

    that.checkedRunIds = [];
    that.checkedNames  = [];

    that.diffWidget.reset();
  }


});});
