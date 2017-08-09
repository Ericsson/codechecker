// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/data/ItemFileWriteStore',
  'dojo/topic',
  'dijit/Dialog',
  'dijit/form/Button',
  'dijit/form/RadioButton',
  'dijit/form/TextBox',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dojox/grid/DataGrid',
  'codechecker/util'],
function (declare, domConstruct, ItemFileWriteStore, topic, Dialog, Button,
  RadioButton, TextBox, BorderContainer, ContentPane, DataGrid, util) {

  function prettifyDuration(seconds) {
    var prettyDuration = "--------";

    if (seconds >= 0) {
      var durHours = Math.floor(seconds / 3600);
      var durMins  = Math.floor(seconds / 60) - durHours * 60;
      var durSecs  = seconds - durMins * 60 - durHours * 3600;

      var prettyDurHours = (durHours < 10 ? '0' : '') + durHours;
      var prettyDurMins  = (durMins  < 10 ? '0' : '') + durMins;
      var prettyDurSecs  = (durSecs  < 10 ? '0' : '') + durSecs;

      prettyDuration
        = prettyDurHours + ':' + prettyDurMins + ':' + prettyDurSecs;
    }

    return prettyDuration;
  }

  /**
   * This function helps to format a data grid cell with two radio buttons.
   * @param args {runData, listOfRunsGrid} - the value from the data store that
   * is passed as a parameter to this function.
   */
  function diffBtnFormatter(args) {
    var infoPane = args.listOfRunsGrid.infoPane;
    var container = new ContentPane({ style : 'padding: 0px' });

    var diffBtnBase = new RadioButton({
      name    : 'diff-base',
      checked : infoPane.baseline &&
                args.runData.runId === infoPane.baseline.runId,
      onClick : function () {
        infoPane.setBaseline(args.runData);
      }
    });

    var diffBtnNew = new RadioButton({
      name    : 'diff-new',
      checked : infoPane.newcheck &&
                args.runData.runId === infoPane.newcheck.runId,
      onClick : function () {
        infoPane.setNewcheck(args.runData);
      }
    });

    container.addChild(diffBtnBase);
    container.addChild(diffBtnNew);

    return container;
  }

  function prettifyStatus(statusCounts) {
    return Object.keys(statusCounts).map(function (statusCount) {
      return util.detectionStatusFromCodeToString(statusCount)
        + '&nbsp;(' + statusCounts[statusCount] + ')';
    }).join(', ');
  }

  var ListOfRunsGrid = declare(DataGrid, {
    constructor : function () {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });

      this.structure = [
        { name : 'Diff', field : 'diff', styles : 'text-align: center;', formatter : diffBtnFormatter},
        { name : 'Run Id', field : 'runid', styles : 'text-align: center;' },
        { name : 'Name', field : 'name', styles : 'text-align: left;', width : '100%' },
        { name : 'Date', field : 'date', styles : 'text-align: center;', width : '30%' },
        { name : 'Number of bugs', field : 'numberofbugs', styles : 'text-align: center;', width : '20%' },
        { name : 'Duration', field : 'duration', styles : 'text-align: center;' },
        { name : 'Check command', field : 'checkcmd', styles : 'text-align: center;' },
        { name : 'Detection status', field : 'detectionstatus', styles : 'text-align: center;', width : '30%' },
        { name : 'Delete', field : 'del', styles : 'text-align: center;', type : 'dojox.grid.cells.Bool', editable : true }
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;

      this._dialog = new Dialog({ title : 'Check command' });
    },

    postCreate : function () {
      this.inherited(arguments);
      this._populateRuns();
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);
      var runId = item.runid[0];

      switch (evt.cell.field) {
        case 'name':
          topic.publish('openRun', item.runData[0]);
          break;

        case 'del':
          if (evt.target.type !== 'checkbox') {
            item.del[0] = !item.del[0];
            this.update();
          }

          if (item.del[0])
            this.infoPane.addToDeleteList(runId);
          else
            this.infoPane.removeFromDeleteList(runId);

          break;

        case 'checkcmd':
          this._dialog.set('content', item.runData[0].runCmd);
          this._dialog.show();

          break;
      }
    },

    /**
     * Sorts run data list by date (newest comes first).
     */
    _sortRunData : function (runDataList) {
      runDataList.sort(function (lhs, rhs) {
        return new Date(rhs.runDate) - new Date(lhs.runDate);
      });
    },

    /**
     * This function refreshes grid with available run data based on text run
     * name filter.
     */
    refreshGrid : function (runNameFilter) {
      var that = this;

      this.store.fetch({
        onComplete : function (runs) {
          runs.forEach(function (run) {
            that.store.deleteItem(run);
          });
          that.store.save();
        }
      });

      CC_SERVICE.getRunData(runNameFilter, function (runDataList) {
        that._sortRunData(runDataList);
        runDataList.forEach(function (item) {
          that._addRunData(item);
        });
      });
    },

    /**
     * This function adds a new run data to the store.
     */
    _addRunData : function (runData) {
      var currItemDate = runData.runDate.split(/[\s\.]+/);
      this.store.newItem({
        id           : runData.runId,
        runid        : runData.runId,
        name         : '<span class="link">' + runData.name + '</span>',
        date         : currItemDate[0] + ' ' + currItemDate[1],
        numberofbugs : runData.resultCount,
        duration     : prettifyDuration(runData.duration),
        runData      : runData,
        checkcmd     : '<span class="link">Show</span>',
        del          : false,
        diff         : { 'runData' : runData, 'listOfRunsGrid' : this },
        detectionstatus : prettifyStatus(runData.detectionStatusCount)
      });
    },

    _populateRuns : function (runNameFilter) {
      var that = this;

      CC_SERVICE.getRunData(runNameFilter, function (runDataList) {
        that._sortRunData(runDataList);

        that.onLoaded(runDataList);
        topic.publish("hooks/RunsListed", runDataList.length);

        runDataList.forEach(function (item) {
          topic.publish("hooks/run/Observed", item);
          that._addRunData(item);
        });
      });
    },

    onLoaded : function (runDataList) {}
  });

  var RunsInfoPane = declare(ContentPane, {
    constructor : function () {
      var that = this;

      this.deleteRunIds = [];

      //--- Text box for searching runs. ---//

      this._runFilter = new TextBox({
        id          : 'runs-filter',
        placeHolder : 'Search for runs...',
        onKeyUp     : function (evt) {
          clearTimeout(this.timer);

          var filter = this.get('value');
          this.timer = setTimeout(function () {
            that.listOfRunsGrid.refreshGrid(filter);
          }, 500);
        }
      });

      //--- Diff Button ---//

      this._diffBtn = new Button({
        label    : 'Diff',
        class    : 'diff-btn',
        disabled : true,
        onClick  : function () {
          topic.publish('openDiff', {
            baseline : that.baseline,
            newcheck : that.newcheck
          });
        }
      });

      //--- Delete Button ---//

      this._deleteBtn = new Button({
        label    : 'Delete',
        class    : 'del-btn',
        disabled : true,
        onClick  : function () {
          that.listOfRunsGrid.store.fetch({
            onComplete : function (runs) {
              runs.forEach(function (run) {
                if (that.deleteRunIds.indexOf(run.runid[0]) !== -1)
                  that.listOfRunsGrid.store.deleteItem(run);
              });
            }
          });

          CC_SERVICE.removeRunResults(that.deleteRunIds, function (success) {});

          that.deleteRunIds = [];
          that.update();
        }
      });
    },

    postCreate : function () {
      this.addChild(this._runFilter);
      this.addChild(this._deleteBtn);
      this.addChild(this._diffBtn);
    },

    addToDeleteList : function (runId) {
      if (this.deleteRunIds.indexOf(runId) === -1)
        this.deleteRunIds.push(runId);
      this.update();
    },

    removeFromDeleteList : function (runId) {
      var index = this.deleteRunIds.indexOf(runId);
      if (index !== -1)
        this.deleteRunIds.splice(index, 1);
      this.update();
    },

    setBaseline : function (runData) {
      if (runData)
        this.baseline = runData;

      this.update();
    },

    setNewcheck : function (runData) {
      if (runData)
        this.newcheck = runData;

      this.update();
    },

    update : function () {
      //--- Update delete button settings. ---//

      this._deleteBtn.set('disabled', this.deleteRunIds.length === 0);

      //--- Update diff button settings. ---//

      var activateDiff = this.baseline && this.newcheck &&
                         this.baseline !== this.newcheck;

      this._diffBtn.set('disabled', !activateDiff);
      this._diffBtn.set('label', activateDiff
        ? 'Diff ' + this.baseline.name + ' to ' + this.newcheck.name
        : 'Diff');
    }
  });

  return declare(BorderContainer, {
    postCreate : function () {
      var that = this;

      var runsInfoPane = new RunsInfoPane({
        region : 'top'
      });

      var listOfRunsGrid = new ListOfRunsGrid({
        region : 'center',
        infoPane : runsInfoPane,
        onLoaded : that.onLoaded
      });

      runsInfoPane.set('listOfRunsGrid', listOfRunsGrid);

      this.addChild(runsInfoPane);
      this.addChild(listOfRunsGrid);
    },

    onLoaded : function (runDataList) {}
  });
});
