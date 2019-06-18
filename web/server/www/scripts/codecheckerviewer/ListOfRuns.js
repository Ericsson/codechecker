// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/data/ObjectStore',
  'dojo/store/api/Store',
  'dojo/Deferred',
  'dojo/topic',
  'dijit/Dialog',
  'dijit/form/Button',
  'dijit/form/RadioButton',
  'dijit/form/TextBox',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dojox/grid/DataGrid',
  'codechecker/AnalyzerStatisticsDialog',
  'codechecker/TabCount',
  'codechecker/util'],
function (declare, dom, ObjectStore, Store, Deferred, topic, Dialog, Button,
  RadioButton, TextBox, BorderContainer, ContentPane, DataGrid,
  AnalyzerStatisticsDialog, TabCount, util) {

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
      var status = util.detectionStatusFromCodeToString(statusCount);

      return '<div class="detection-status-wrapper" title="' + status + '">'
        +'<i class="customIcon detection-status-' + status.toLowerCase()
        + '"></i><span class="num">(' + statusCounts[statusCount]
        + ')</span></div>';
    }).join(', ');
  }

  function versionTagFormatter(param) {
    var versionTag = util.createRunTag(param.runName, param.versionTag,
      util.getTooltip('versionTag'));

    return versionTag ? versionTag.outerHTML : '';
  }

  function numberOfUnresolvedBugsFormatter (num) {
    return '<span title="' + util.getTooltip('numOfUnresolved') + '">'
      + num + '</span>'
  }

  function runNameFormatter(args) {
    var runData = args.runData;

    var label = '<span class="link">' + runData.name + '</span>';

    var ctuEnabled = runData.runCmd.indexOf('--ctu') !== -1;
    var statsEnabled = runData.runCmd.indexOf('--stats') !== -1;
    if (ctuEnabled || statsEnabled) {
      label += '<span class="run-name-labels">';
      if (ctuEnabled) {
        label += '<span class="label ctu">ctu</span>';
      }

      if (statsEnabled) {
        label += '<span class="label stats">stats</span>';
      }
      label += '</span>';
    }

    return label;
  }

  var RunStore = declare(Store, {
    constructor : function (listOfRunsGrid) {
      this.listOfRunsGrid = listOfRunsGrid;
    },

    getIdentity : function (run) {
      return run.runId;
    },

    query : function (query, options) {
      var deferred = new Deferred();
      deferred.total = query.total;

      var that = this;
      CC_SERVICE.getRunData(
        query.runFilter,
        CC_OBJECTS.MAX_QUERY_SIZE,
        options.start,
        function (runDataList) {
          if (runDataList instanceof RequestFailed) {
            deferred.reject('Failed to get runs: ' + runDataList.message);
          } else {
            deferred.resolve(that._formatItems(runDataList));
          }
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });

      return deferred;
    },

    _formatItems : function(runDataList) {
      var that = this;
      runDataList = runDataList.map(function (runData) {
        return {
          id           : runData.runId,
          runid        : runData.runId,
          name         : { 'runData' : runData },
          versionTag   : { runName : runData.name,
                           versionTag : runData.versionTag },
          date         : util.prettifyDate(runData.runDate),
          numberofbugs : runData.resultCount,
          duration     : util.prettifyDuration(runData.duration),
          runData      : runData,
          checkcmd     : '<span class="link">Show</span>',
          del          : false,
          diff         : { 'runData' : runData,
                           'listOfRunsGrid' : that.listOfRunsGrid },
          detectionstatus : prettifyStatus(runData.detectionStatusCount),
          codeCheckerVersion : runData.codeCheckerVersion,
          analyzerStatistics : runData.analyzerStatistics
        };
      });

      return runDataList;
    }
  });

  var ListOfRunsGrid = declare(DataGrid, {
    constructor : function () {

      this.store = new ObjectStore({
        objectStore : new RunStore(this)
      });

      this.structure = [
        { name : 'Diff', field : 'diff', styles : 'text-align: center;', formatter : diffBtnFormatter},
        { name : 'Name', field : 'name', styles : 'text-align: left;', width : '100%', formatter: runNameFormatter },
        { name : '<span title="' + util.getTooltip('numOfUnresolved') + '">Number of unresolved reports</span>', field : 'numberofbugs', formatter: numberOfUnresolvedBugsFormatter, styles : 'text-align: center;', width : '20%' },
        { name : '<span title="' + util.getTooltip('detectionStatus') + '">Detection status</span>', field : 'detectionstatus', styles : 'text-align: center;', width : '30%' },
        { name : 'Analyzer statistics', field : 'analyzerStatistics', styles : 'text-align: center;', width : '30%', formatter : util.analyzerStatisticsFormatter },
        { name : 'Storage date', field : 'date', styles : 'text-align: center;', width : '25%' },
        { name : 'Analysis duration', field : 'duration', styles : 'text-align: center;' },
        { name : 'Check command', field : 'checkcmd', styles : 'text-align: center;' },
        { name : '<span title="' + util.getTooltip('versionTag') + '">Version tag</span>', field : 'versionTag', formatter : versionTagFormatter },
        { name : 'CodeChecker version', field : 'codeCheckerVersion' },
        { name : 'Delete', field : 'del', styles : 'text-align: center;', type : 'dojox.grid.cells.Bool', editable : true }
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

    canSort : function (inSortInfo) {
      var cell = this.getCell(Math.abs(inSortInfo) - 1);

      return cell.field === 'name' ||
             cell.field === 'numberofbugs'   ||
             cell.field === 'date' ||
             cell.field === 'duration'    ||
             cell.field === 'codeCheckerVersion';
    },

    postCreate : function () {
      this.inherited(arguments);
      this.layout.setColumnVisibility(7, this.get('showDelete'));

      this.refreshGrid();
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);
      var runId = item.runid;

      switch (evt.cell.field) {
        case 'name':
          if (!evt.target.classList.contains('link'))
            return;

          var runName = item.runData.name;
          topic.publish('openRun', {
            baseline : runName,
            tabId : runName,
            openedByUserEvent : true
          });
          break;

        case 'del':
          if (evt.target.type !== 'checkbox') {
            item.del = !item.del;
            this.update();
          }

          if (item.del)
            this.infoPane.addToDeleteList(runId);
          else
            this.infoPane.removeFromDeleteList(runId);

          break;

        case 'checkcmd':
          this._dialog.set('title', 'Check command');
          this._dialog.set('content', item.runData.runCmd);
          this._dialog.show();

          break;

        case 'analyzerStatistics':
          var stats = item.runData.analyzerStatistics;
          if (Object.keys(stats).length) {
            this._analyzerStatDialog.show(item.runData.analyzerStatistics);
          }

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
    refreshGrid : function (runFilter) {
      var that = this;

      var total = new Deferred();
      CC_SERVICE.getRunCount(runFilter, function (count) {
          total.resolve(count);
          that._updateRunCount(count);
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });

      this.setQuery({
        runFilter: runFilter,
        total: total
      });

      // In Firefox the onLoaded function called immediately before topics
      // have been registered.
      setTimeout(function () { that.onLoaded(); }, 0);
    },

    _updateRunCount : function (num) {
      this.parent.set('tabCount', num);
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

          var runNameFilter = this.get('value');
          this.timer = setTimeout(function () {
            var runFilter = new CC_OBJECTS.RunFilter();
            runFilter.names = [runNameFilter + '*'];
            that.listOfRunsGrid.refreshGrid(runFilter);
          }, 500);
        }
      });

      //--- Diff Button ---//

      this._diffBtn = new Button({
        label    : 'Diff',
        class    : 'diff-btn',
        disabled : true,
        onClick  : function () {
          topic.publish('openRun', {
            baseline : that.baseline.name,
            newcheck : that.newcheck.name,
            tabId : that.baseline.name + '_diff_' + that.newcheck.name,
            openedByUserEvent : true
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
              var runCount = runs.length;
              runs.forEach(function (run) {
                if (that.deleteRunIds.indexOf(run.runid[0]) !== -1) {
                  that.listOfRunsGrid.store.deleteItem(run);
                  --runCount;
                }
              });
              that.listOfRunsGrid._updateRunCount(runCount);
            }
          });

          that.deleteRunIds.forEach(function (runId) {
            CC_SERVICE.removeRun(runId, function () {}).fail(
            function (jsReq, status, exc) {
              new Dialog({
                title : 'Failure!',
                content : exc.message
              }).show();
              util.handleAjaxFailure(jsReq);
            });
          });

          that.deleteRunIds = [];
          that.update();
        }
      });
    },

    postCreate : function () {
      this.addChild(this._runFilter);

      if (this.get('showDelete'))
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

  return declare([BorderContainer, TabCount], {
    postCreate : function () {
      this.inherited(arguments);

      var showDelete = false;
      try {
        showDelete = CC_AUTH_SERVICE.hasPermission(
          Permission.PRODUCT_STORE, util.createPermissionParams({
            productID : CURRENT_PRODUCT.id
          }));
      } catch (ex) { util.handleThriftException(ex); }

      var runsInfoPane = new RunsInfoPane({
        region : 'top',
        showDelete : showDelete
      });

      var listOfRunsGrid = new ListOfRunsGrid({
        region : 'center',
        infoPane : runsInfoPane,
        parent : this,
        onLoaded : this.onLoaded,
        showDelete : showDelete
      });

      runsInfoPane.set('listOfRunsGrid', listOfRunsGrid);

      this.addChild(runsInfoPane);
      this.addChild(listOfRunsGrid);
    },

    onLoaded : function (runDataList) {}
  });
});
