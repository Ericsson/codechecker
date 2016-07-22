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
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dojox/grid/DataGrid'],
function (declare, domConstruct, ItemFileWriteStore, topic, Dialog, Button,
  BorderContainer, ContentPane, DataGrid) {

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

  var ListOfRunsGrid = declare(DataGrid, {
    constructor : function () {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });

      this.structure = [
        { name : 'Diff', field : 'diff', styles : 'text-align: center;', type : 'dojox.grid.cells.Bool', editable : true },
        { name : 'Run Id', field : 'runid', styles : 'text-align: center;' },
        { name : 'Name', field : 'name', styles : 'text-align: left;', width : '100%' },
        { name : 'Date', field : 'date', styles : 'text-align: center;', width : '30%' },
        { name : 'Number of bugs', field : 'numberofbugs', styles : 'text-align: center;', width : '20%' },
        { name : 'Duration', field : 'duration', styles : 'text-align: center;' },
        { name : 'Check command', field : 'checkcmd', styles : 'text-align: center;' },
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

        case 'diff':
          if (evt.target.type !== 'checkbox') {
            item.diff[0] = !item.diff[0];
            this.update();
          }

          var items = this.getItemsWhere(function (item) {
            return item.diff[0];
          });

          if (item.diff[0])
            if (items.length === 1)
              this.infoPane.setBaseline(item.runData[0]);
            else if (items.length === 2)
              this.infoPane.setNewcheck(item.runData[0]);
            else
              item.diff[0] = false;
          else
            if (items.length === 0)
              this.infoPane.setBaseline(null);
            else if (items.length === 1) {
              this.infoPane.setNewcheck(null);
              this.infoPane.setBaseline(items[0].runData[0]);
            }

          this.update();

          break;

        case 'checkcmd':
          this._dialog.set('content', item.runData[0].runCmd);
          this._dialog.show();

          break;
      }
    },

    getItemsWhere : function (func) {
      var result = [];

      for (var i = 0; i < this.rowCount; ++i) {
        var item = this.getItem(i);
        if (func(item))
          result.push(item);
      }

      return result;
    },

    _populateRuns : function () {
      var that = this;

      CC_SERVICE.getRunData(function (runDataList) {
        that.onLoaded(runDataList);

        runDataList.forEach(function (item) {
          var currItemDate = item.runDate.split(/[\s\.]+/);

          that.store.newItem({
            diff : false,
            id : item.runId,
            runid : item.runId,
            name : '<span class="link">' + item.name + '</span>',
            date : currItemDate[0] + ' ' + currItemDate[1],
            numberofbugs : item.resultCount,
            duration : prettifyDuration(item.duration),
            del : false,
            runData : item,
            checkcmd : '<span class="link">Show</span>'
          });
        });
      });
    },

    onLoaded : function (runDataList) {}
  });

  var RunsInfoPane = declare(ContentPane, {
    constructor : function () {
      this.deleteRunIds = [];
      this.style = 'padding: 2px';
    },

    postCreate : function () {
      var that = this;
      this.inherited(arguments);

      //--- Diff Button ---//

      this.diffBtn = new Button({
        label : 'Diff',
        disabled : true,
        onClick : function () {
          topic.publish('openDiff', {
            baseline : that.baseline,
            newcheck : that.newcheck
          });
        }
      });

      this.addChild(this.diffBtn);

      //--- Baseline and newcheck displays ---//

      var baselineDiv = domConstruct.create('div', {
        innerHTML : 'Baseline: ',
        class : 'diffDisplay'
      });

      var newcheckDiv = domConstruct.create('div', {
        innerHTML : 'NewCheck: ',
        class : 'diffDisplay'
      });

      this.baselineSpan
        = domConstruct.create('span', { innerHTML : '-' }, baselineDiv);
      this.newcheckSpan
        = domConstruct.create('span', { innerHTML : '-' }, newcheckDiv);

      domConstruct.place(baselineDiv, this.domNode);
      domConstruct.place(newcheckDiv, this.domNode);

      //--- Delete Button ---//

      this.deleteBtn = new Button({
        label : 'Delete',
        class : 'deleteButton',
        disabled : true,
        onClick : function () {
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

      this.addChild(this.deleteBtn);
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
      if (runData) {
        this.baselineSpan.innerHTML = runData.runId;
        this.baseline = runData;
      } else {
        this.baselineSpan.innerHTML = '-';
        this.baseline = undefined;
      }
      this.update();
    },

    setNewcheck : function (runData) {
      if  (runData) {
        this.newcheckSpan.innerHTML = runData.runId;
        this.newcheck = runData;
      } else {
        this.newcheckSpan.innerHTML = '-';
        this.newcheck = undefined;
      }
      this.update();
    },

    update : function () {
      this.deleteBtn.set('disabled', this.deleteRunIds.length === 0);
      this.diffBtn.set('disabled',
        this.baselineSpan.innerHTML === '-' ||
        this.newcheckSpan.innerHTML === '-')
    }
  });

  return declare(BorderContainer, {
    postCreate : function () {
      var that = this;

      var runsInfoPane = new RunsInfoPane({
        region : 'bottom'
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
