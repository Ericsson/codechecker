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
  "scripts/codecheckerviewer/ListOfRunsGrid.js",
  "scripts/codecheckerviewer/OverviewTC.js",
  "scripts/codecheckerviewer/Util.js",
  "scripts/codecheckerviewer/widgets/ListOfRunsWidget.js",
  "scripts/codecheckerviewer/widgets/MenuButton.js",
], function (declare, hash, topic, ioQuery, BorderContainer, TabContainer,
  ContentPane, ListOfRunsGrid, OverviewTC, Util, ListOfRunsWidget,
  MenuButton) {
return declare(null, {


  constructor : function() {
    var that = this;

    that.diffRuns = [];
    that.deleteRunIds = [];

    that.initGlobals();

    that.initCCV();
  },


  /**
   * Initializes the global variables to be used.
   */
  initGlobals : function() {
    CC_SERVICE = new codeCheckerDBAccess.codeCheckerDBAccessClient(
      new Thrift.Protocol(new Thrift.Transport("CodeCheckerService")));
    CC_UTIL    = new Util();
  },


  /**
   * Initializes the Viewer
   */
  initCCV : function() {
    var that = this;

    CC_SERVICE.getSuppressFile(function(filePath) {
      that.isSupprFileAvailable = (filePath !== "");

      var initialHash = hash();

      that.buildLayout();
      that.buildListOfRuns();
      that.buildMenuButton();
      that.layout.startup();
      that.listOfRunsGrid.fillGridWithRunData();
      that.listOfRunsGrid.render();

      topic.subscribe("/dojo/hashchange", function(changedHash) {
        that.handleHashChange(changedHash);
      });

      // Restore previous state from cuttent hash (if any).
      if (hash() != initialHash) {
        hash(initialHash);
      } else {
        that.handleHashChange(initialHash);
      }

      that.listOfRunsBC.onShow = function() {
        if (hash() != "") {
          hash("");
          that.listOfRunsGrid.render();
        }
      };

    });
  },


  /**
   * Builds the layout and the uppermost containers.
   */
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


  /**
   * Creates the ListOfRuns view which consists of a ListOfRunsGrid and a
   * ListOfRunsWidget and their appropriate encapsulating Containers.
   */
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
      style         : "font-family: sans-serif; padding: 0px; margin: 0px; border: 0px;",
      onRowClick    : function(evt) {

        switch (evt.cell.field) {

          case "name":

            var tempRunId = that.listOfRunsGrid.getItem(evt.rowIndex).runid[0];
            var tempName = that.listOfRunsGrid.getItem(evt.rowIndex).name[0];

            that.newRunOverviewTab(tempRunId, tempName);

            break;

          case "deleteDisplay":
            var tempDelete = that.listOfRunsGrid.getItem(evt.rowIndex).deleteActual[0];

            if (tempDelete) {
              that.listOfRunsGrid.getItem(evt.rowIndex).deleteActual[0] = false;
              that.listOfRunsGrid.getItem(evt.rowIndex).deleteDisplay[0] = false;
              that.listOfRunsGrid.update();

              for (var i = 0, len = that.deleteRunIds.length ; i < len ; ++i) {
                if (that.listOfRunsGrid.getItem(evt.rowIndex).runid[0] == that.deleteRunIds[i]) {
                  that.deleteRunIds.splice(i, 1);
                  break;
                }
              }
            } else {
              that.listOfRunsGrid.getItem(evt.rowIndex).deleteActual[0] = true;
              that.listOfRunsGrid.getItem(evt.rowIndex).deleteDisplay[0] = true;
              that.listOfRunsGrid.update();

              that.deleteRunIds.push(that.listOfRunsGrid.getItem(evt.rowIndex).runid[0]);
            }

            if (that.deleteRunIds.length === 0) {
              that.listOfRunsWidget.setDeleteButtonDisabled(true);
            } else {
              that.listOfRunsWidget.setDeleteButtonDisabled(false);
            }

            break;

          case "diffDisplay":

            var tempDiff = that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0];
            var diffNumber = that.listOfRunsGrid.getDiffNumber();

            if (tempDiff) {

              that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0] = false;
              that.listOfRunsGrid.getItem(evt.rowIndex).diffDisplay[0] = false;
              that.listOfRunsGrid.update();

              for(var i = 0 ; i < diffNumber ; ++i) {
                if (that.diffRuns[i].runId === that.listOfRunsGrid.getItem(evt.rowIndex).runid[0]) {
                  that.diffRuns.splice(i, 1);
                  break;
                }
              }

            } else {

              if (diffNumber < 2) {
                that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0] = true;
                that.listOfRunsGrid.getItem(evt.rowIndex).diffDisplay[0] = true;
                that.listOfRunsGrid.update();

                that.diffRuns.push({
                  runId : that.listOfRunsGrid.getItem(evt.rowIndex).runid[0],
                  runName : that.listOfRunsGrid.getItem(evt.rowIndex).name[0]
                });

              } else {
                that.listOfRunsGrid.getItem(evt.rowIndex).diffActual[0] = false;
                that.listOfRunsGrid.getItem(evt.rowIndex).diffDisplay[0] = false;
                that.listOfRunsGrid.update();
              }

            }

            diffNumber = that.listOfRunsGrid.getDiffNumber();

            if (diffNumber === 2) {
              that.listOfRunsWidget.setDiffButtonDisabled(false);
            } else {
              that.listOfRunsWidget.setDiffButtonDisabled(true);
            }


            if (diffNumber === 0) {
              that.listOfRunsWidget.setDiffLabel("-", "-");
            } else if (diffNumber === 1) {
              that.listOfRunsWidget.setDiffLabel(that.diffRuns[0].runId, "-");
            } else {
              that.listOfRunsWidget.setDiffLabel(that.diffRuns[0].runId,
                that.diffRuns[1].runId);
            }

            break;

        }

      }
    });


    that.listOfRunsWidget = new ListOfRunsWidget();


    that.listOfRunsBC = new BorderContainer({
      id     : "bc_listofrunsgrid",
      title  : that.listOfRunsGrid.title
    });


    that.listOfRunsGridCP = new ContentPane({
      region : "center",
      style  : "margin: 0px; padding: 0px;"
    });

    that.listOfRunsWidgetCP = new ContentPane({
      region : "bottom",
      style  : "margin: 0px; padding: 0px;"
    });


    that.listOfRunsGridCP.addChild(that.listOfRunsGrid);
    that.listOfRunsWidgetCP.addChild(that.listOfRunsWidget);

    that.listOfRunsBC.addChild(that.listOfRunsGridCP);
    that.listOfRunsBC.addChild(that.listOfRunsWidgetCP);

    that.mainTC.addChild(that.listOfRunsBC);
  },


  /**
   * Creates and places the MenuButton on the headerPane.
   */
  buildMenuButton : function() {
    var that = this;

    var menuButton = new MenuButton({
      mainTC : that.mainTC,
    });

    that.headerPane.addChild(menuButton);
  },


  /**
   * This function gets called when the Delete button in the ListOfRunsWidget
   * is pressed
   */
  deleteRuns : function() {
    var that = this;

    CC_SERVICE.removeRunResults(that.deleteRunIds, function(isSuccessful) {
      if (isSuccessful) {
        that.reset();
      } else {
        console.log("Removal of runs failed.");
      }
    });
  },


  /**
   * Handling of the change of the browser history/hash happens here. It is
   * called if necessary after a dojo/hashchange event.
   *
   * @param changedHash a browser hash (different than the current hash)
   */
  handleHashChange : function(changedHash) {
    var that = this;

    if (!changedHash) {
      that.mainTC.selectChild("bc_listofrunsgrid");
    }

    var hashState = ioQuery.queryToObject(changedHash);
    if (!hashState) {
      return;
    }

    var ovId = CC_UTIL.getOverviewIdFromHashState(hashState);
    if (undefined !== dijit.byId(ovId)) {
      that.mainTC.selectChild(dijit.byId(ovId));
      return;
    }

    if (hashState.ovType == 'run') {
      that.handleNewRunOverviewTab(
        ovId,
        hashState.ovRunId,
        hashState.ovName);
    } else if (hashState.ovType == 'diff') {
      that.handleNewDiffOverviewTab(
        ovId,
        hashState.diffRunIds[0],
        hashState.diffRunIds[1],
        hashState.diffNames[0],
        hashState.diffNames[1]
      );
    }
  },


  /**
   * This is the first step in creating a new RunOverview tab.
   */
  newRunOverviewTab : function(runId, runName) {
    var hashState = {
      ovType: 'run',
      ovName: runName,
      ovRunId: runId
    };

    hash(ioQuery.objectToQuery(hashState));
  },


  /**
   * This is the first step in creating a new DiffOverview tab, changes the hash
   * appropriately.
   */
  newDiffOverviewTab : function(runId1, runId2, runName1, runName2) {
    var hashState = {
      ovType: 'diff',
      diffNames: [runName1, runName2],
      diffRunIds: [runId1, runId2]
    };

    hash(ioQuery.objectToQuery(hashState));
  },


    /**
   * Creates a new DiffOverview tab, it may be called after a dojo/hashchange event.
   */
  handleNewRunOverviewTab : function(idOfNewOverviewTC, runId, runName) {
    var that = this;

    CC_UTIL.getCheckerTypeAndSeverityCountsForRun(runId, function(filterOptions) {
      var newOverviewTC = new OverviewTC({
        id           : idOfNewOverviewTC,
        runId        : runId,
        overviewType : "run",
        filterOptions: filterOptions,
        title        : runName,
        closable     : true,
        style        : "padding: 5px;",
        onClose      : function() {
          if (that.mainTC.selectedChildWidget === newOverviewTC) {
            that.mainTC.selectChild("bc_listofrunsgrid");
          }

          newOverviewTC.hashchangeHandle.remove();

          return true;
        },
        onShow : function() {
          that.newRunOverviewTab(runId, runName);
        }
      });

      try {
        that.mainTC.addChild(newOverviewTC);
        that.mainTC.selectChild(newOverviewTC);

        newOverviewTC.overviewGrid.startup();
      } catch (err) {
        newOverviewTC.destroyRecursive();
        console.log(err);
      }
    });
  },


  /**
   * Creates a new DiffOverview tab, it may be called after a dojo/hashchange event.
   */
  handleNewDiffOverviewTab : function(idOfNewOverviewTC, runId1, runId2, runName1, runName2) {
    var that = this;

    var newOverviewTC = new OverviewTC({
      id           : idOfNewOverviewTC,
      runId1       : runId1,
      runId2       : runId2,
      overviewType : "diff",
      title        : "Diff of " + runName1 + " and " + runName2,
      closable     : true,
      style        : "padding: 5px;",
      onClose      : function() {
        if (that.mainTC.selectedChildWidget === newOverviewTC) {
          that.mainTC.selectChild("bc_listofrunsgrid");
        }

        newOverviewTC.hashchangeHandle.remove();

        return true;
      },
      onShow : function() {
        that.newDiffOverviewTab(runId1, runId2, runName1, runName2);
      }
    });

    try {
      that.mainTC.addChild(newOverviewTC);
      that.mainTC.selectChild(newOverviewTC);

      newOverviewTC.overviewGrid.startup();
    } catch (err) {

      newOverviewTC.destroyRecursive();
      console.log(err);

    }

  },


  /**
   * Resets the whole ListOfRuns view to the original starting state.
   */
  reset : function() {
    var that = this;

    that.listOfRunsGrid.recreateStore();
    that.listOfRunsGrid.fillGridWithRunData()
    that.listOfRunsGrid.render();

    that.diffRuns = [];
    that.deleteRunIds = [];

    that.listOfRunsWidget.reset();
  }


});});
