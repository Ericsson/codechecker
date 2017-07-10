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
  'codechecker/hashHelper',
  'codechecker/BugViewer',
  'codechecker/filterHelper',
  'codechecker/util'],
function (declare, dom, Deferred, ObjectStore, Store, QueryResults, topic,
  BorderContainer, TabContainer, Tooltip, DataGrid, hashHelper, BugViewer,
  filterHelper, util) {

  var filterHook = function(query, isDiff) {
    var length;
    if (query.reportFilters.length > 1)
      length = query.reportFilters.length;
    else {
      var onlyFilter = query.reportFilters[0];
      if (onlyFilter.filepath !== "**" || onlyFilter.checkerId ||
          onlyFilter.checkerMsg || onlyFilter.severity)
        length = 1;
      else
        length = null; // null indicates default filters.
    }

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
      var that = this;
      var deferred = new Deferred();

      CC_SERVICE.getRunResults(
        query.runData.runId,
        CC_OBJECTS.MAX_QUERY_SIZE,
        options.start,
        (options.sort || []).map(this._toSortMode),
        query.reportFilters,
        function (reportDataList) {
          if (reportDataList instanceof RequestFailed)
            deferred.reject('Failed to get reports: ' + reportDataList.message);
          else {
            deferred.resolve(that._formatItems(reportDataList));
            filterHook(query, false);
          }
        });

      deferred.total = CC_SERVICE.getRunResultCount(
        query.runData.runId,
        query.reportFilters);

      return deferred;
    },

    _formatItems : function (reportDataList) {
      reportDataList.forEach(function (reportData) {
        reportData.checkedFile = reportData.checkedFile +
          ' @ Line ' + reportData.lastBugPosition.startLine;

        //--- Review status ---//

        var className = util.reviewStatusCssClass(reportData.review.status);
        var reviewStatus =
          util.reviewStatusFromCodeToString(reportData.review.status);

        reportData.reviewStatusHtml = '<span title="' + reviewStatus
          + '" class="customIcon review-status-' + className + '"></span>'
          + reviewStatus;

        reportData.reviewComment = reportData.review.comment;
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
        : CC_OBJECTS.SortType.SEVERITY;
      sortMode.ord
        = sort.descending
        ? CC_OBJECTS.Order.DESC
        : CC_OBJECTS.Order.ASC;

      return sortMode;
    }
  });

  var DiffBugStore = declare(BugStore, {
    query : function (query, options) {
      var that = this;
      var deferred = new Deferred();

      switch (query.difftype + '') {
        default:
        case 'new':
          CC_SERVICE.getNewResults(
            query.baseline.runId,
            query.newcheck.runId,
            CC_OBJECTS.MAX_QUERY_SIZE,
            options.start,
            (options.sort || []).map(this._toSortMode),
            query.reportFilters,
            function (reportDataList) {
              if (reportDataList instanceof RequestFailed)
                deferred.reject(
                  'Failed to get reports: ' + reportDataList.message);
              else {
                deferred.resolve(that._formatItems(reportDataList));
                filterHook(query, true);
              }
            });
          break;

        case 'resolved':
          CC_SERVICE.getResolvedResults(
            query.baseline.runId,
            query.newcheck.runId,
            CC_OBJECTS.MAX_QUERY_SIZE,
            options.start,
            (options.sort || []).map(this._toSortMode),
            query.reportFilters,
            function (reportDataList) {
              if (reportDataList instanceof RequestFailed)
                deferred.reject(
                  'Failed to get reports: ' + reportDataList.message);
              else {
                deferred.resolve(that._formatItems(reportDataList));
                filterHook(query, true);
              }
            });
          break;

        case 'unresolved':
          CC_SERVICE.getUnresolvedResults(
            query.baseline.runId,
            query.newcheck.runId,
            CC_OBJECTS.MAX_QUERY_SIZE,
            options.start,
            (options.sort || []).map(this._toSortMode),
            query.reportFilters,
            function (reportDataList) {
              if (reportDataList instanceof RequestFailed)
                deferred.reject(
                  'Failed to get reports: ' + reportDataList.message);
              else {
                deferred.resolve(that._formatItems(reportDataList));
                filterHook(query, true);
              }
            });
          break;
      }

      return deferred;
    }
  });

  function severityFormatter(severity) {
    // When loaded from URL then report data is originally a number.
    // When loaded by clicking on a table row, then severity is already
    // changed to its string representation.
    if (typeof severity === 'number')
      severity = util.severityFromCodeToString(severity);

    var title = severity.charAt(0).toUpperCase() + severity.slice(1);
    return '<span title="' + title  + '" class="icon-severity icon-severity-'
      + severity + '"></span>';
  }

  var ListOfBugsGrid = declare(DataGrid, {
    constructor : function () {
      var width = (100 / 5).toString() + '%';

      this.structure = [
        { name : 'File', field : 'checkedFile', cellClasses : 'link compact', width : '100%' },
        { name : 'Message', field : 'checkerMsg', width : '100%' },
        { name : 'Checker name', field : 'checkerId', cellClasses : 'link', width : '50%' },
        { name : 'Severity', field : 'severity', cellClasses : 'severity', formatter : severityFormatter },
        { name : 'Review status', field : 'reviewStatusHtml', cellClasses : 'review-status', width : '25%' },
        { name : 'Review comment', cellClasses : 'review-comment-message compact', field : 'reviewComment', width : '50%' }
        { name : 'Detection status', field : 'detectionStatus' },
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
      this.setQuery({
        runData : this.runData,
        reportFilters : reportFilters
      });
    },

    canSort : function (inSortInfo) {
      var cell = this.getCell(Math.abs(inSortInfo) - 1);

      return cell.field === 'checkedFile' ||
             cell.field === 'checkerId'   ||
             cell.field === 'severity'    ||
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
          item.runId = this.runData.runId;
          topic.publish('openFile', item, this);
          break;

        case 'checkerId':
          topic.publish('showDocumentation', item.checkerId);
          break;
      }
    },

    onRowMouseOver : function (evt) {
      var item = this.getItem(evt.rowIndex);
      switch (evt.cell.field) {
        case 'reviewComment':
          if (item.review.comment) {
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

  var ListOfBugsDiffGrid = declare(ListOfBugsGrid, {
    constructor : function () {
      this.store = new ObjectStore({ objectStore : new DiffBugStore() });
    },

    refreshGrid : function (reportFilters, difftype) {
      this._difftype = difftype || 'new';

      this.setQuery({
        baseline : this.baseline,
        newcheck : this.newcheck,
        reportFilters : reportFilters,
        difftype : difftype
      });
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);

      this._lastSelectedRow = evt.rowIndex;

      switch (evt.cell.field) {
        case 'checkedFile':
          item.runId
            = this.difftype === 'new'
            ? this.newcheck.runId
            : this.baseline.runId;
          topic.publish('openFile', item, this);
          break;

        case 'checkerId':
          topic.publish('showDocumentation', item.checkerId);
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
          hashHelper.removeReport();
        }
      });

      //--- Filter ---//

      var filterGroup
        = this.runData
        ? new filterHelper.FilterGroup({
            runId : this.runData.runId,
            filters : this.filters
          })
        : new filterHelper.FilterGroup({
            baselineId : this.baseline.runId,
            newcheckId : this.newcheck.runId,
            filters : this.filters
          });

      filterGroup.set('region', 'top');
      filterGroup.onChange = function (allValues) {
        hashHelper.setFilter(filterGroup);
        grid.refreshGrid(
          filterHelper.filterGroupToReportFilters(filterGroup, allValues),
          allValues[0].difftype);

        that._difftype = allValues[0].difftype;
      };

      filterGroup.onAddFilter = function () {
        content.resize();
        hashHelper.setFilter(filterGroup);
       };

      filterGroup.onRemoveFilter = function () {
        content.resize();
        hashHelper.setFilter(filterGroup);
       };

      content.addChild(filterGroup);

      //--- Grid ---//

      var grid
        = this.runData
        ? new ListOfBugsGrid({
            region : 'center',
            runData : this.runData
          })
        : new ListOfBugsDiffGrid({
            region : 'center',
            baseline : this.baseline,
            newcheck : this.newcheck
          });

      grid.refreshGrid(filterHelper.filterGroupToReportFilters(filterGroup));
      content.addChild(grid);

      this.addChild(content);

      //--- Events ---//

      this._openFileTopic = topic.subscribe('openFile',
      function (reportData, sender) {
        if (sender && sender !== grid)
          return;

        if (!(reportData instanceof CC_OBJECTS.ReportData))
          reportData = CC_SERVICE.getReport(reportData);

        var filename = reportData.checkedFile.substr(
          reportData.checkedFile.lastIndexOf('/') + 1);

        var runData = that.runData;

        if (!runData)
          runData
            = filter.getValue('difftype') === 'new'
            ? that.newcheck
            : that.baseline;

        var bugViewer = new BugViewer({
          title : filename,
          closable : true,
          reportData : reportData,
          runData : runData,
          onShow : function () {
            hashHelper.setReport(reportData.reportId);
          }
        });

        that.addChild(bugViewer);
        that.selectChild(bugViewer);

        topic.publish('showComments', reportData.reportId, bugViewer._editor);
      });
    },

    destroy : function () {
      this.inherited(arguments);
      this._openFileTopic.remove();
      // Clear URL if list of bugs view is closed.
      hashHelper.clear();
    }
  });
});
