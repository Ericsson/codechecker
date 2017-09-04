// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
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
  'codechecker/BugFilterView',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, dom, Deferred, ObjectStore, Store, QueryResults, topic,
  BorderContainer, TabContainer, Tooltip, DataGrid, BugViewer, BugFilterView,
  hashHelper, util) {

  var filterHook = function(filters, isDiff) {
    var length = 0;

    Object.keys(filters).map(function (key) {
      if (filters[key])
        length += filters[key].length;
    })

    topic.publish("hooks/FilteringChanged" + (isDiff ? "Diff" : ""), length);
  };

  var createRunResultFilterParameter = function (reportFilters) {
    var cmpData = null;
    var runIds = null;
    if (reportFilters.run)
      runIds = reportFilters.run;
    else if (reportFilters.baseline || reportFilters.newcheck) {
      runIds = reportFilters.baseline;

      if (reportFilters.newcheck) {
        cmpData = new CC_OBJECTS.CompareData();
        cmpData.run_ids = reportFilters.newcheck;
        cmpData.diff_type = reportFilters.difftype
          ? reportFilters.difftype
          : CC_OBJECTS.DiffType.NEW;
      }
    }

    return {
      runIds  : runIds,
      cmpData : cmpData
    };
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
      var that = this;
      var deferred = new Deferred();

      var runResultParam = createRunResultFilterParameter(query.reportFilters);

      CC_SERVICE.getRunResults_v2(
        runResultParam.runIds,
        CC_OBJECTS.MAX_QUERY_SIZE,
        options.start,
        (options.sort || []).map(this._toSortMode),
        query.reportFilters,
        runResultParam.cmpData,
        function (reportDataList) {
          if (reportDataList instanceof RequestFailed)
            deferred.reject('Failed to get reports: ' + reportDataList.message);
          else {
            deferred.resolve(that._formatItems(reportDataList));
            filterHook(query.reportFilters, false);
          }
        });

      deferred.total = CC_SERVICE.getRunResultCount_v2(runResultParam.runIds,
        query.reportFilters, runResultParam.cmpData);

      return deferred;
    },

    _formatItems : function (reportDataList) {
      reportDataList.forEach(function (reportData) {
        reportData.checkedFile = reportData.checkedFile +
          ' @ Line ' + reportData.line;

        //--- Review status ---//

        var review = reportData.reviewData;
        reportData.reviewStatus = review.status;
        reportData.reviewComment = review.author && review.comment
          ? review.comment
          : review.author ? '-' : '';
      });

      return reportDataList;
    },

    _toSortMode : function (sort) {
      var sortMode = new CC_OBJECTS.SortMode();

      sortMode.type
        = sort.attribute === 'checkedFile'
        ? CC_OBJECTS.SortType.FILENAME
        : sort.attribute === 'checkerId'
        ? CC_OBJECTS.SortType.CHECKER_NAME
        : sort.attribute === 'detectionStatus'
        ? CC_OBJECTS.SortType.DETECTION_STATUS
        : sort.attribute === 'reviewStatus'
        ? CC_OBJECTS.SortType.REVIEW_STATUS
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
    var status = util.detectionStatusFromCodeToString(detectionStatus);

    return '<span title="' + status  + '" class="customIcon detection-status-'
      + status.toLowerCase() + '"></span>';
  }

  function reviewStatusFormatter(reviewStatus) {
    var className = util.reviewStatusCssClass(reviewStatus);
    var status =
      util.reviewStatusFromCodeToString(reviewStatus);

    return '<span title="' + status
      + '" class="customIcon ' + className + '"></span>';
  }

  var ListOfBugsGrid = declare(DataGrid, {
    constructor : function () {
      var width = (100 / 5).toString() + '%';

      this.structure = [
        { name : 'File', field : 'checkedFile', cellClasses : 'link compact', width : '100%' },
        { name : 'Message', field : 'checkerMsg', width : '100%' },
        { name : 'Checker name', field : 'checkerId', cellClasses : 'link', width : '50%' },
        { name : 'Severity', field : 'severity', cellClasses : 'severity', width : '15%', formatter : severityFormatter },
        { name : 'Review status', field : 'reviewStatus', cellClasses : 'review-status', width : '15%', formatter : reviewStatusFormatter },
        { name : 'Review comment', cellClasses : 'review-comment-message compact', field : 'reviewComment', width : '50%' },
        { name : 'Detection status', field : 'detectionStatus', cellClasses : 'detection-status', width : '15%', formatter : detectionStatusFormatter }
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.store = new ObjectStore({ objectStore : new BugStore() });
      this.escapeHTMLInData = false;
      this.selectionMode = 'single';
      this._lastSelectedRow = 0;
    },

    refreshGrid : function (reportFilters) {
      this.setQuery({ reportFilters : reportFilters });
    },

    canSort : function (inSortInfo) {
      var cell = this.getCell(Math.abs(inSortInfo) - 1);

      return cell.field === 'checkedFile' ||
             cell.field === 'checkerId'   ||
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

      switch (evt.cell.field) {
        case 'checkedFile':
          topic.publish('openFile', item, this.runData, this);
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
        case 'reviewComment':
          if (item.review.author) {
            var content = util.reviewStatusTooltipContent(item.review);

            Tooltip.show(content.outerHTML, evt.target, ['below']);
          }
          break;
      }
    },

    onCellMouseOut : function (evt) {
      switch (evt.cell.field) {
        case 'reviewComment':
          Tooltip.hide(evt.target);
          break;
      }
    }
  });

  return declare(TabContainer, {
    postCreate : function () {
      var that = this;

      var content = new BorderContainer({
        title : 'Bug Overview',
        onShow : function () {
          grid.scrollToLastSelected();
          hashHelper.setStateValue('report', null);
        }
      });

      //--- Bug filters ---//

      this._bugFilterView = new BugFilterView({
        class    : 'bug-filters',
        region   : 'left',
        style    : 'width: 300px; padding: 0px;',
        splitter : true,
        diffView : this.baseline || this.newcheck || this.difftype,
        parent   : this,
        runData  : this.runData,
        baseline : this.baseline,
        newcheck : this.newcheck,
        difftype : this.difftype
      });

      content.addChild(this._bugFilterView);

      //--- Grid ---//

      var grid = new ListOfBugsGrid({
        region : 'center',
        runData : this.runData,
        baseline : this.baseline,
        newcheck : this.newcheck,
        difftype : this.difftype
      });

      grid.refreshGrid(that._bugFilterView.getReportFilters());
      content.addChild(grid);

      this.addChild(content);

      //--- Events ---//

      this._openFileTopic = topic.subscribe('openFile',
      function (reportData, runData, sender) {
        if (sender && sender !== grid)
          return;

        if (!that.runData && !that.baseline && !that.allReportView)
          return;

        if (!(reportData instanceof CC_OBJECTS.ReportData))
          reportData = CC_SERVICE.getReport(reportData);

        var filename = reportData.checkedFile.substr(
          reportData.checkedFile.lastIndexOf('/') + 1);

        var reportFilters = that._bugFilterView.getReportFilters();
        var runResultParam = createRunResultFilterParameter(reportFilters);
        if (runData)
          runResultParam.runIds = [runData.runId];

        var bugViewer = new BugViewer({
          title : filename,
          closable : true,
          reportData : reportData,
          runData : runData ? runData : that.runData,
          runResultParam : runResultParam,
          onShow : function () {
            hashHelper.setStateValue('report', reportData.reportId);
          }
        });

        that.addChild(bugViewer);
        that.selectChild(bugViewer);

        topic.publish('showComments', reportData.reportId, bugViewer._editor);
      });

      this._filterChangeTopic = topic.subscribe('filterchange',
      function (state) {
        if (state.parent !== that._bugFilterView)
          return;

        var reportFilters = that._bugFilterView.getReportFilters();
        grid.refreshGrid(reportFilters);
      });
    },

    onShow : function () {
      var state  = this._bugFilterView.getState();
      state.report = null;

      if (this.allReportView)
        state.allReports = true;

      hashHelper.setStateValues(state);

      //--- Call show method of the selected children ---//

      this.getChildren().forEach(function (child) {
        if (child.selected)
          child.onShow();
      });
    },

    onHide : function () {
      if (this.allReportView)
        hashHelper.setStateValue('allReports', null);
    },

    destroy : function () {
      this.inherited(arguments);
      this._openFileTopic.remove();
      this._filterChangeTopic.remove();
      // Clear URL if list of bugs view is closed.
      hashHelper.clear();
    }
  });
});
