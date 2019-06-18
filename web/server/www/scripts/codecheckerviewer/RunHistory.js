// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/data/ObjectStore',
  'dojo/store/api/Store',
  'dojo/Deferred',
  'dojox/grid/DataGrid',
  'dijit/Dialog',
  'dijit/layout/ContentPane',
  'codechecker/AnalyzerStatisticsDialog',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, ObjectStore, Store, Deferred, DataGrid, Dialog, ContentPane,
  AnalyzerStatisticsDialog, hashHelper, util) {

  var formatDate = function (date) {
    var mm = date.getMonth() + 1; // getMonth() is zero-based
    var dd = date.getDate();

    return [date.getFullYear(),
            (mm > 9 ? '' : '0') + mm,
            (dd > 9 ? '' : '0') + dd
            ].join('-') + ' ' +
            [date.getHours(),
            date.getMinutes(),
            date.getSeconds() + (date.getMilliseconds() > 0 ? 1 : 0)
            ].join(':');
  };

  var RunHistoryStore = declare(Store, {
    query : function (query, options) {
      var deferred = new Deferred();
      if (!query.total) {
        return deferred.reject('ERROR!');
      }

      deferred.total = query.total;

      var that = this;
      CC_SERVICE.getRunHistory(
        query.runIds,
        CC_OBJECTS.MAX_QUERY_SIZE,
        options.start,
        null,
        function (runHistories) {
          if (runHistories instanceof RequestFailed) {
            deferred.reject('Failed to get run histories: ' +
              runHistories.message);
          } else {
            deferred.resolve(that._formatItems(runHistories));
          }
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });

      return deferred;
    },

    _formatItems : function(runHistories) {
      return runHistories.map(function (runHistory) {
        return {
          id: runHistory.id,
          name: runHistory.runName,
          user: runHistory.user,
          date: util.prettifyDate(runHistory.time),
          checkCommand: '<span class="link">Show</span>',
          versionTag: { runName : runHistory.runName,
                        versionTag : runHistory.versionTag },
          codeCheckerVersion : runHistory.codeCheckerVersion,
          analyzerStatistics : runHistory.analyzerStatistics,
          runCmd: runHistory.checkCommand
        };
      });
    }
  });

  function runNameFormatter(runName) {
    return '<span class="link">' + runName + '</span>';
  }

  function versionTagFormatter(param) {
    var versionTag = util.createRunTag(param.runName, param.versionTag,
      util.getTooltip('versionTag'));

    return versionTag ? versionTag.outerHTML : '';
  }

  var ListOfRunHistoryGrid = declare(DataGrid, {
    constructor : function () {
      this.store = new ObjectStore({
        objectStore : new RunHistoryStore()
      });

      this.structure = [
        { name : 'Name', field : 'name', styles : 'text-align: left;', width : '100%', formatter: runNameFormatter },
        { name : 'Analyzer statistics', field : 'analyzerStatistics', styles : 'text-align: center;', width : '30%', formatter : util.analyzerStatisticsFormatter },
        { name : 'Date', field : 'date', styles : 'text-align: center;', width : '25%' },
        { name : 'User', field : 'user', styles : 'text-align: center;', width : '25%' },
        { name : 'Check command', field : 'checkCommand', styles : 'text-align: center;' },
        { name : '<span title="' + util.getTooltip('versionTag') + '">Version tag</span>', field : 'versionTag', formatter: versionTagFormatter },
        { name : 'CodeChecker version', field : 'codeCheckerVersion', width : '25%' },
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;
      this.rowsPerPage = CC_OBJECTS.MAX_QUERY_SIZE;

      this._dialog = new Dialog({
        style : 'max-width: 75%; min-width: 25%'
      });

      this._analyzerStatDialog = new AnalyzerStatisticsDialog();
    },

    canSort : function () {
      return false;
    },

    openRunHistory : function (runName, versionTag, time) {
      var filter = this.bugFilterView;
      this.bugFilterView.clearAll();

      if (filter._runBaseLineFilter)
        filter._runBaseLineFilter.select(runName);

      filter._detectionStatusFilter.selectDefaultValues();
      filter._reviewStatusFilter.selectDefaultValues();

      if (!versionTag) {
        var date = new Date(time.replace(/ /g,'T'));
        filter._detectionDateFilter.initFixedDateInterval(formatDate(date));
      } else {
        filter._runHistoryTagFilter.select(runName + ':' + versionTag);
      }

      this.bugFilterView.notifyAll();
      hashHelper.setStateValues({subtab : null});
    },

    onRowClick : function (evt) {
      var that = this;

      var item = this.getItem(evt.rowIndex);

      switch (evt.cell.field) {
        case 'name':
          if (!evt.target.classList.contains('link')) {
            return;
          }

          this.openRunHistory(item.name, item.versionTag.versionTag, item.date);
          break;

        case 'checkCommand':
          CC_SERVICE.getCheckCommand(item.id, null,
          function (checkCommand) {
            if (!checkCommand) {
              checkCommand = 'Unavailable!';
            }

            that._dialog.set('title', 'Check command');
            that._dialog.set('content', checkCommand);
            that._dialog.show();
          }).fail(function (xhr) { util.handleAjaxFailure(xhr); });

          break;

        case 'analyzerStatistics':
          var stats = item.analyzerStatistics;
          if (Object.keys(stats).length) {
            this._analyzerStatDialog.show(stats);
          }

          break;
      }
    },

    /**
     * This function refreshes grid with available run history data based on
     * the given run history filter.
     */
    refreshGrid : function (runIds, filter) {
      var total = new Deferred();
      CC_SERVICE.getRunHistoryCount(runIds, filter, function (count) {
          total.resolve(count);
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });

      this.setQuery({
        runIds: runIds,
        runHistoryFilter: filter,
        total: total
      });
    }
  });

  return declare(ContentPane, {
    postCreate : function () {
      this._runHistoryGrid = new ListOfRunHistoryGrid({
        bugFilterView : this.bugFilterView
      });

      this.addChild(this._runHistoryGrid);
    },

    initRunHistory : function (runNames) {
      var that = this;

      this.startup();

      if (!runNames)
        runNames = [];

      // Check if we should update the current run history.
      if (this.runNames &&
          runNames.sort().toString() === this.runNames.sort().toString()
      ) {
        return;
      }

      this.runNames = runNames;

      // Get run history.
      if (runNames.length) {
        var runFilter = new CC_OBJECTS.RunFilter();
        runFilter.names = runNames;

        CC_SERVICE.getRunData(runFilter, null, 0, function (runData) {
          var runIds = runData.map(function (run) { return run.runId; });
          that._runHistoryGrid.refreshGrid(runIds);
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      } else {
        this._runHistoryGrid.refreshGrid();
      }
    },
  });
});
