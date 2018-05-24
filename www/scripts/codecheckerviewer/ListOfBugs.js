// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/dom-style',
  'dojo/Deferred',
  'dojo/data/ObjectStore',
  'dojo/store/api/Store',
  'dojo/store/util/QueryResults',
  'dojo/topic',
  'dijit/layout/BorderContainer',
  'dijit/layout/TabContainer',
  'dijit/Tooltip',
  'dojox/grid/DataGrid',
  'codechecker/BugViewer',
  'codechecker/filter/BugFilterView',
  'codechecker/filter/FilterBase',
  'codechecker/RunHistory',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, dom, style, Deferred, ObjectStore, Store, QueryResults,
  topic, BorderContainer, TabContainer, Tooltip, DataGrid, BugViewer,
  BugFilterView, FilterBase, RunHistory, hashHelper, util) {

  function getRunData(runIds, runNames) {
    var runFilter = new CC_OBJECTS.RunFilter();

      if (runIds) {
        if (!(runIds instanceof Array))
          runIds = [runIds];

        runFilter.ids = runIds;
      }

      if (runNames) {
        if (!(runNames instanceof Array))
          runNames = [runNames];

        runFilter.names = runNames;
        runFilter.exactMatch = true;
      }

    var runData = CC_SERVICE.getRunData(runFilter);
    return runData.length ? runData[0] : null;
  }

  function initByUrl(grid, tab) {
    var state = hashHelper.getValues();

    if (!(state.tab === undefined && tab === 'allReports') && tab !== state.tab)
      return;

    if (state.report !== undefined || state.reportHash !== undefined) {
      topic.publish('openFile',
        state.report !== undefined ? state.report : null,
        state.reportHash !== undefined ? state.reportHash : null,
        grid);
      return;
    }

    switch (state.subtab) {
      case undefined:
        topic.publish('subtab/bugOverview');
        return;
      case 'runHistory':
        topic.publish('subtab/runHistory');
        return;
    }
  }

  var filterHook = function(filters, isDiff) {
    var length = 0;

    if (!filters) return;

    Object.keys(filters).map(function (key) {
      if (filters[key])
        length += filters[key].length;
    })

    topic.publish("hooks/FilteringChanged" + (isDiff ? "Diff" : ""), length);
  };

  var BugStore = declare(Store, {
    constructor : function () {
      this.sortType = [];
    },

    get : function (id) {
      var deferred = new Deferred();

      CC_SERVICE.getReport(id, function (reportData) {
        if (typeof reportData === 'string')
          deferred.reject('Failed to get report ' + id + ': ' + reportData);
        else
          deferred.resolve(reportData);
      });

      return deferred;
    },

    getIdentity : function (reportData) {
      return reportData.reportId;
    },

    query : function (query, options) {
      var deferred = new Deferred();

      // It is possible that this method will be called before we set the
      // correct filter parameters for example when we first open a run.
      if (!query.reportFilter)
        return deferred.reject("ERROR!");

      var that = this;
      CC_SERVICE.getRunResults(
        query.runIds,
        CC_OBJECTS.MAX_QUERY_SIZE,
        options.start,
        options.sort ? options.sort.map(this._toSortMode) : null,
        query.reportFilter,
        query.cmpData,
        function (reportDataList) {
          if (reportDataList instanceof RequestFailed)
            deferred.reject('Failed to get reports: ' + reportDataList.message);
          else {
            deferred.resolve(that._formatItems(reportDataList));
            filterHook(query.reportFilters, false);
          }
        });

      return deferred;
    },

    _formatItems : function (reportDataList) {
      reportDataList.forEach(function (reportData) {
        reportData.file = {
          line : reportData.line,
          file : reportData.checkedFile
        };

        //--- Review status ---//

        var review = reportData.reviewData;
        reportData.reviewStatus = review.status;
      });

      return reportDataList;
    },

    _toSortMode : function (sort) {
      var sortMode = new CC_OBJECTS.SortMode();

      sortMode.type
        = sort.attribute === 'file'
        ? CC_OBJECTS.SortType.FILENAME
        : sort.attribute === 'checkerId'
        ? CC_OBJECTS.SortType.CHECKER_NAME
        : sort.attribute === 'detectionStatus'
        ? CC_OBJECTS.SortType.DETECTION_STATUS
        : sort.attribute === 'reviewStatus'
        ? CC_OBJECTS.SortType.REVIEW_STATUS
        : sort.attribute === 'bugPathLength'
        ? CC_OBJECTS.SortType.BUG_PATH_LENGTH
        : CC_OBJECTS.SortType.SEVERITY;
      sortMode.ord
        = sort.descending
        ? CC_OBJECTS.Order.DESC
        : CC_OBJECTS.Order.ASC;

      return sortMode;
    }
  });

  function severityFormatter(severity) {
    // When loaded from URL then report data is originally a number.
    // When loaded by clicking on a table row, then severity is already
    // changed to its string representation.
    if (typeof severity === 'number')
      severity = util.severityFromCodeToString(severity);

    var title = severity.charAt(0).toUpperCase() + severity.slice(1);
    return '<span title="' + title  + '" class="customIcon icon-severity-'
      + severity + '"></span>';
  }

  function detectionStatusFormatter(detectionStatus) {
    if (detectionStatus !== null) {
      var status = util.detectionStatusFromCodeToString(detectionStatus);

      return '<span title="' + status  + '" class="customIcon detection-status-'
        + status.toLowerCase() + '"></span>';
    }

    return 'N/A';
  }

  function reviewStatusFormatter(reviewStatus) {
    var className = util.reviewStatusCssClass(reviewStatus);
    var status =
      util.reviewStatusFromCodeToString(reviewStatus);

    return '<span title="' + status
      + '" class="customIcon ' + className + '"></span>';
  }

  function checkerMessageFormatter(msg) {
    return msg !== null ? msg : 'N/A';
  }

  function fileFormatter(obj) {
    return '<span class="link">' + (obj.line
      ? obj.file + ' @ Line ' + obj.line
      : obj.file) + '</span>';
  }

  function checkerNameFormatter(checkerId) {
    return '<span class="link">' + checkerId + '</span>';
  }

  function bugPathLengthFormatter(length) {
    var d = dom.create('span', { innerHTML : length, class : 'length' });
    var blendColor = util.getBugPathLenColor(length);
    style.set(d, 'background-color', blendColor);

    return d.outerHTML;
  }

  var ListOfBugsGrid = declare([DataGrid, FilterBase], {
    constructor : function () {
      var width = (100 / 5).toString() + '%';

      this.structure = [
        { name : 'File', field : 'file', cellClasses : 'compact', width : '100%', formatter: fileFormatter },
        { name : 'Message', field : 'checkerMsg', width : '100%', formatter : checkerMessageFormatter },
        { name : 'Checker name', field : 'checkerId', width : '50%', formatter: checkerNameFormatter },
        { name : 'Severity', field : 'severity', cellClasses : 'severity', width : '15%', formatter : severityFormatter },
        { name : 'Bug path length', field : 'bugPathLength', cellClasses : 'bug-path-length', width : '15%', formatter : bugPathLengthFormatter },
        { name : 'Review status', field : 'reviewStatus', cellClasses : 'review-status', width : '15%', formatter : reviewStatusFormatter },
        { name : '<span title="' + util.getTooltip('detectionStatus') + '">Detection status</span>', field : 'detectionStatus', cellClasses : 'detection-status', width : '15%', formatter : detectionStatusFormatter }
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.store = new ObjectStore({ objectStore : new BugStore() });
      this.escapeHTMLInData = false;
      this.selectionMode = 'single';
      this.rowsPerPage = CC_OBJECTS.MAX_QUERY_SIZE;
      this._lastSelectedRow = 0;
    },

    notify : function () {
      this.setQuery({
        runIds : this.bugFilterView.getRunIds(),
        reportFilter : this.bugFilterView.getReportFilter(),
        cmpData : this.bugFilterView.getCmpData()
      });
    },

    canSort : function (inSortInfo) {
      var cell = this.getCell(Math.abs(inSortInfo) - 1);

      return cell.field === 'bugPathLength' ||
             cell.field === 'checkerId'   ||
             cell.field === 'file' ||
             cell.field === 'severity'    ||
             cell.field === 'reviewStatus' ||
             cell.field === 'detectionStatus';
    },

    scrollToLastSelected : function () {
      this.scrollToRow(this._lastSelectedRow);
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);

      this._lastSelectedRow = evt.rowIndex;

      if (!evt.target.classList.contains('link'))
        return;

      switch (evt.cell.field) {
        case 'file':
          topic.publish('openFile', item, item.bugHash, this);
          break;

        case 'checkerId':
          topic.publish('showDocumentation', item.checkerId);
          break;
      }
    },

    onRowMouseOver : function (evt) {
      if (!evt.cell)
        return;

      var item = this.getItem(evt.rowIndex);
      switch (evt.cell.field) {
        case 'reviewStatus':
          if (item.reviewData.author) {
            var content = util.reviewStatusTooltipContent(item.reviewData);
            Tooltip.show(content.outerHTML, evt.target, ['below']);
          }
          break;
      }
    },

    onCellMouseOut : function (evt) {
      switch (evt.cell.field) {
        case 'reviewStatus':
          Tooltip.hide(evt.target);
          break;
      }
    }
  });

  return declare(TabContainer, {
    constructor : function () {
      this._bugViewerHashToTab = {};
      this._subscribeTopics();
    },

    postCreate : function () {
      var that = this;

      this._grid = new ListOfBugsGrid({
        region : 'center'
      });

      this._bugOverview = new BorderContainer({
        title : 'Bug Overview',
        iconClass : 'customIcon list-opened',
        onShow : function () {
          // When opening a run first this onShow method will be called multiple
          // times. That is the reason why we check that the show method is
          // already in progress.
          if (this._showInProgress)
            return true;

          this._showInProgress = true;
          var state  = that._bugFilterView.getUrlState();
          state.tab  = that.tab;
          state.report = null;
          state.reportHash = null;
          state.subtab = null;

          hashHelper.resetStateValues(state);

          // If the filter has not been initalized then we should initalize it.
          if (!that._bugFilterView.isInitalized()) {
            if (that.baseline && !state.run)
              state.run = this.baseline;
            if (that.newcheck && !state.newcheck)
              state.newcheck = that.newcheck;

            var self = this;
            setTimeout(function () {
              that._bugFilterView.initAll(state);
              that._grid.scrollToLastSelected();
              self._showInProgress = false;
            }, 0);
          } else {
            this._showInProgress = false;
          }
        }
      });

      //--- Bug filters ---//

      this._bugFilterView = new BugFilterView({
        class    : 'bug-filters',
        region   : 'left',
        style    : 'width: 320px; padding: 0px;',
        splitter : true,
        parent   : this,
        diffView : this.newcheck,
        openedByUserEvent : this.openedByUserEvent,
        baseline : this.baseline,
        newcheck : this.newcheck
      });
      this._grid.set('bugFilterView', this._bugFilterView);
      this._bugFilterView.register(this._grid);

      // Call the notify explicitly to initalize grid filters.
      this._grid.notify();

      //--- Run history ---//

      this._runHistory = new RunHistory({
        title : 'Run history',
        iconClass : 'customIcon run',
        runData : this.runData,
        bugOverView : this._bugOverview,
        bugFilterView : this._bugFilterView,
        parent : this,
        onShow : function () {
          if (!this.initalized)
            this.initRunHistory();

          var state = hashHelper.getState();

          hashHelper.resetStateValues({
            'tab' : state.tab,
            'subtab' : 'runHistory'
          });
          that.subtab = 'runHistory';
          this.initalized = true;
        }
      });

      this._bugOverview.addChild(this._bugFilterView);

      this._bugOverview.addChild(this._grid);
      this.addChild(this._bugOverview);

      this.addChild(this._runHistory);

      var state = hashHelper.getState();
      if (state.tab === that.tab && state.subtab !== that.subtab)
        initByUrl(this._grid, this.tab);
    },

    _subscribeTopics : function () {
      var that = this;

      this._runHistoryTopic = topic.subscribe('subtab/runHistory', function () {
        that.selectChild(that._runHistory);
      });

      this._bugOverviewTopic = topic.subscribe('subtab/bugOverview', function () {
        that.selectChild(that._bugOverview);
      });

      this._hashChangeTopic = topic.subscribe('/dojo/hashchange',
      function (url) {
        var state = hashHelper.getState();
        if (state.tab === that.tab && state.subtab !== that.subtab)
          initByUrl(that._grid, that.tab);
      });

      this._openFileTopic = topic.subscribe('openFile',
      function (reportData, reportHash, sender) {
        if (sender && sender !== that._grid)
          return;

        if (reportData !== null && !(reportData instanceof CC_OBJECTS.ReportData))
          reportData = CC_SERVICE.getReport(reportData);

        var getAndUseReportHash = reportHash && (!reportData ||
          reportData.reportId === null || reportData.bugHash !== reportHash);

        if (getAndUseReportHash) {
          // Get all reports by report hash
          var reportFilter = new CC_OBJECTS.ReportFilter();
          reportFilter.reportHash = [reportHash];
          reportFilter.isUnique = false;

          if (reportData)
            reportFilter.filepath = ['*' + reportData.checkedFile];

          // We set a sort option to select a report which has the shortest
          // bug path length.
          var sortMode = new CC_OBJECTS.SortMode();
          sortMode.type = CC_OBJECTS.SortType.BUG_PATH_LENGTH;
          sortMode.ord = CC_OBJECTS.Order.ASC;

          // Get run ids by the filter set.
          var runIds = [];
          var opt = that._bugFilterView.initReportFilterOptions();
          if (opt.runIds)
            runIds = runIds.concat(opt.runIds);
          if (opt.cmpData && opt.cmpData.runIds)
            runIds = runIds.concat(opt.cmpData.runIds);

          reports = CC_SERVICE.getRunResults(runIds.length ? runIds : null,
            CC_OBJECTS.MAX_QUERY_SIZE, 0, [sortMode], reportFilter, null);
          reportData = reports[0];
        }

        if (that.reportData &&
            that.reportData.reportId === reportData.reportId) {
          var tab = that._bugViewerHashToTab[reportData.bugHash];
          if (tab)
            that.selectChild(tab);
          return;
        }

        that.reportData = reportData;

        var filename = reportData.checkedFile.substr(
          reportData.checkedFile.lastIndexOf('/') + 1);

        var bugViewer = new BugViewer({
          title : filename,
          iconClass : 'customIcon bug',
          closable : true,
          reportData : reportData,
          runIds : [reportData.runId],
          listOfBugsGrid : that._grid,
          onShow : function () {
            hashHelper.setStateValues({
              'reportHash' : reportData.bugHash,
              'report' : reportData.reportId,
              'subtab' : reportData.bugHash
            });
            that.subtab = reportData.bugHash;
          },
          onClose : function () {
            delete that._bugViewerHashToTab[reportData.bugHash];
            that.reportData = null;

            topic.publish('subtab/bugOverview');

            return true;
          }
        });
        that.addChild(bugViewer);
        that.selectChild(bugViewer);

        // Remove the old child with the same report hash if it's exists
        if (that._bugViewerHashToTab[reportData.bugHash])
          that.removeChild(that._bugViewerHashToTab[reportData.bugHash]);

        that._bugViewerHashToTab[reportData.bugHash] = bugViewer;

        topic.publish('showComments', reportData.reportId, bugViewer._editor);
      });
    },

    onShow : function () {
     // Call show method of the selected children.
     this.getChildren().forEach(function (child) {
       if (child.selected)
         child.onShow();
     });
    },

    destroy : function () {
      this.inherited(arguments);
      this._openFileTopic.remove();
      this._hashChangeTopic.remove();
      this._bugOverviewTopic.remove();
      this._runHistoryTopic.remove();

      // Clear URL if list of bugs view is closed.
      hashHelper.clear();
    }
  });
});
