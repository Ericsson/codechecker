// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojo/data/ItemFileWriteStore',
  'dojo/dom-construct',
  'dojo/Deferred',
  'dojo/promise/all',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dojo/topic',
  'dojox/form/CheckedMultiSelect',
  'dojox/grid/DataGrid',
  'dojox/widget/Standby',
  'dijit/form/CheckBox',
  'dijit/layout/ContentPane',
  'dijit/layout/BorderContainer',
  'codechecker/CheckerStatisticsFilter',
  'codechecker/hashHelper',
  'codechecker/filter/BugFilterView',
  'codechecker/filter/FilterBase',
  'codechecker/util'],
function (declare, lang, ItemFileWriteStore, dom, Deferred, all, Memory,
  Observable, topic, CheckedMultiSelect, DataGrid, Standby, CheckBox,
  ContentPane, BorderContainer, CheckerStatisticsFilter, hashHelper,
  BugFilterView, FilterBase, util) {

  function severityFormatter(severity) {
    var severity = util.severityFromCodeToString(severity);

    var title = severity.charAt(0).toUpperCase() + severity.slice(1);
    return '<span title="' + title  + '" class="link customIcon icon-severity-'
      + severity + '" style="cursor: pointer;"></span>';
  }

  function checkerNameFormatter(checkerName) {
    return '<span class="link">' + checkerName + '</span>';
  }

  function numberFormatter(num) {
    return !num ? '' : '<span class="link">' + num + '</span>';
  }

  var CheckerStatistics = declare([DataGrid, FilterBase], {
    constructor : function (args) {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });

      this.structure = [
        { name : 'Checker', field : 'checker', width : '100%', formatter : checkerNameFormatter},
        { name : 'Severity', field : 'severity', styles : 'text-align: center;', width : '15%', formatter : severityFormatter},
        { name : '<span class="customIcon detection-status-unresolved"></span> All reports', field : 'reports', width : '20%', formatter : numberFormatter},
        { name : '<span class="customIcon detection-status-resolved"></span> Resolved', field : 'resolved', width : '20%', formatter : numberFormatter},
        { name : '<span class="customIcon review-status-unreviewed"></span> Unreviewed', field : 'unreviewed', width : '20%', formatter : numberFormatter},
        { name : '<span class="customIcon review-status-confirmed-bug"></span>Confirmed bug', field : 'confirmed', width : '20%', formatter : numberFormatter},
        { name : '<span class="customIcon review-status-false-positive"></span> False positive', field : 'falsePositive', width : '20%', formatter : numberFormatter},
        { name : "<span class= \"customIcon review-status-intentional\"></span>Intentional", field : 'intentional', width : '20%', formatter : numberFormatter}
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.autoHeight = true;
      this.escapeHTMLInData = false;
      this.sortInfo = -2; // sort by severity
    },

    onRowClick : function (evt) {
      if (!evt.target.classList.contains('link'))
        return;

      var item = this.getItem(evt.rowIndex);

      var filter = this.bugFilterView;
      var reviewFilter = filter._reviewStatusFilter;
      var detectionFilter = filter._detectionStatusFilter;

      // Clear the filters.
      filter.clearAll();

      var statisticsFilterState = this.filter.getUrlState();
      filter.getFilters().forEach(function (filter) {
        filter.initByUrl(statisticsFilterState);
      });
      filter._isInitalized = true;

      // Select the checker name.
      filter._checkerNameFilter.select(item.checker);

      switch (evt.cell.field) {
        case 'checker':
        case 'reports':
          break;
        case 'severity':
          filter._severityFilter.select(
            filter._severityFilter.stateConverter(item.severity[0]));
          break;
        case 'resolved':
          if (!item.resolved[0]) return;

          detectionFilter.select(detectionFilter.stateConverter(
            CC_OBJECTS.DetectionStatus.RESOLVED));
          break;
        case 'unreviewed':
          if (!item.unreviewed[0]) return;

          reviewFilter.select(reviewFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.UNREVIEWED));
          break;
        case 'confirmed':
          if (!item.confirmed[0]) return;

          reviewFilter.select(reviewFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.CONFIRMED));
          break;
        case 'falsePositive':
          if (!item.falsePositive[0]) return;

          reviewFilter.select(reviewFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.FALSE_POSITIVE));
          break;
        case 'intentional':
          if (!item.intentional[0]) return;

          reviewFilter.select(reviewFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.INTENTIONAL));
          break;
        default:
          return;
      }

      filter.notifyAll();
      topic.publish('tab/allReports');
    },

    refreshGrid : function (runIds, reportFilter) {
      var that = this;

      this.standBy.show();

      this.store.fetch({
        onComplete : function (runs) {
          runs.forEach(function (run) {
            that.store.deleteItem(run);
          });
          that.store.save();
        }
      });

      this._populateStatistics(runIds, reportFilter);
    },

    _populateStatistics : function (runIds, reportFilter) {
      var that = this;

      var query = [
        {},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.UNREVIEWED]},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.CONFIRMED]},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.FALSE_POSITIVE]},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.INTENTIONAL]},
        {field : 'detectionStatus', values : [CC_OBJECTS.DetectionStatus.RESOLVED]}
      ].map(function (q) {
        var deferred = new Deferred();

        var filter = lang.clone(reportFilter);
        if (q.field)
          filter[q.field] = q.values;

        var limit = null;
        var offset = null;
        CC_SERVICE.getCheckerCounts(runIds, filter, null, limit, offset,
        function (res) {
          var obj = {};
          res.forEach(function (item) { obj[item.name] = item; });
          deferred.resolve(obj);
        });

        return deferred.promise;
      });

      all(query).then(function (res) {
        var checkers = res[0];
        Object.keys(checkers).map(function (key) {
          that.store.newItem({
            id            : key,
            checker       : key,
            severity      : checkers[key].severity,
            reports       : checkers[key].count,
            unreviewed    : res[1][key] !== undefined ? res[1][key].count : 0,
            confirmed     : res[2][key] !== undefined ? res[2][key].count : 0,
            falsePositive : res[3][key] !== undefined ? res[3][key].count : 0,
            intentional   : res[4][key] !== undefined ? res[4][key].count : 0,
            resolved      : res[5][key] !== undefined ? res[5][key].count : 0
          });
        });
        that.sort();
        that.standBy.hide();
      });
    },

    notify : function () {
      var runIds = this.filter.getRunIds();
      var reportFilter = this.filter.getReportFilter();
      this.refreshGrid(runIds, reportFilter);
    },

    exportToCSV : function () {
      this.store.fetch({
        onComplete : function (statistics) {
          var content = [['Checker', 'Severity', 'All reports', 'Resolved',
            'Unreviewed', 'Confirmed bug', 'False positive', 'Intentional']];
          statistics.forEach(function (stat) {
            content.push([stat.checker,
              util.severityFromCodeToString(stat.severity), stat.reports,
              stat.resolved, stat.unreviewed, stat.confirmed,
              stat.falsePositive, stat.intentional
            ]);
          });
          util.exportToCSV('cc_checker_statistics.csv', content);
        }
      });
    }
  });

  var SeverityStatistics = declare([DataGrid, FilterBase], {
    constructor : function (args) {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });

      this.structure = [
        { name : 'Severity', field : 'severity', styles : 'text-align: center;', width : '15%', formatter : severityFormatter},
        { name : '<span class="customIcon detection-status-unresolved"></span> All reports', field : 'reports', width : '20%', formatter : numberFormatter},
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.autoHeight = true;
      this.escapeHTMLInData = false;
      this.sortInfo = -1; // sort by severity
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);

      var filter = this.bugFilterView;
      var runNameFilter = filter._runBaseLineFilter;
      var severityFilter = filter._severityFilter;

       // Clear the filters.
      filter.clearAll();

      var statisticsFilterState = this.filter.getUrlState();
      filter.getFilters().forEach(function (filter) {
        filter.initByUrl(statisticsFilterState);
      });
      filter._isInitalized = true;

      switch (evt.cell.field) {
        case 'severity':
        case 'reports':
          severityFilter.select(
            severityFilter.stateConverter(item.severity[0]));
          break;
        default:
          return;
      }

      filter.notifyAll();
      topic.publish('tab/allReports');
    },

    refreshGrid : function (runIds, reportFilter) {
      var that = this;

      this.standBy.show();

      this.store.fetch({
        onComplete : function (statistics) {
          statistics.forEach(function (statistic) {
            that.store.deleteItem(statistic);
          });
          that.store.save();
        }
      });

      this._populateStatistics(runIds, reportFilter);
    },

    _populateStatistics : function (runIds, reportFilter) {
      var that = this;

      var limit = null;
      var offset = null;
      CC_SERVICE.getSeverityCounts(runIds, reportFilter, null, limit, offset,
      function (res) {
        for (key in res) {
          that.store.newItem({
            id : key,
            severity : key,
            reports : res[key]
          });
        }
        that.sort();
        that.standBy.hide();
      });
    },

    notify : function () {
      var runIds = this.filter.getRunIds();
      var reportFilter = this.filter.getReportFilter();
      this.refreshGrid(runIds, reportFilter);
    },

    exportToCSV : function () {
      this.store.fetch({
        onComplete : function (statistics) {
          var content = [['Severity', 'Reports']];
          statistics.forEach(function (stat) {
            content.push([
              util.severityFromCodeToString(stat.severity),
              stat.reports
            ]);
          });
          util.exportToCSV('cc_severity_statistics.csv', content);
        }
      });
    }
  });

  return declare(BorderContainer, {
    postCreate : function () {
      this._standBy = new Standby({
        color : '#ffffff',
        target : this.domNode,
        duration : 0
      });
      this.addChild(this._standBy);

      //--- Statistics filter bar ---//

      this._statisticsFilter = new CheckerStatisticsFilter({
        class : 'bug-filters',
        region : 'left',
        style : 'width: 320px; padding: 0px;',
        splitter : true,
        parent : this,
      });
      this.addChild(this._statisticsFilter);

      //--- Statistics table ---//

      var centerPane = new ContentPane({
        region : 'center'
      });

      //--- Checker statistics table ---//

      this._checkerStatistics = new CheckerStatistics({
        class : 'checker-statistics-list',
        bugFilterView : this.listOfAllReports._bugFilterView,
        filter : this._statisticsFilter,
        standBy : this._standBy
      });
      this._createHeader(centerPane, 'Checker statistics',
        this._checkerStatistics);
      centerPane.addChild(this._checkerStatistics);
      this._statisticsFilter.register(this._checkerStatistics);

      //--- Severity statistics table ---//

      this._severityStatistics = new SeverityStatistics({
        class : 'severity-statistics-list',
        bugFilterView : this.listOfAllReports._bugFilterView,
        filter : this._statisticsFilter,
        standBy : this._standBy
      });
      this._createHeader(centerPane, 'Severity statistics',
        this._severityStatistics);
      centerPane.addChild(this._severityStatistics);
      this._statisticsFilter.register(this._severityStatistics);

      this.addChild(centerPane);
    },

    onShow : function () {
      if (!this.initalized) {
        this.initalized = true;

        // Call the notify explicitly to initialize grid filters.
        this._checkerStatistics.notify();
        this._severityStatistics.notify();
      }

      var state  = this._statisticsFilter.getUrlState();
      state.tab  = this.tab;
      hashHelper.resetStateValues(state);
    },

    _createHeader : function (parent, title, grid) {
      var wrapper = dom.create('div', {
        class : 'statistic-header-wrapper'
      }, parent.domNode);

      dom.create('span', {
        class : 'title',
        innerHTML : title
      }, wrapper);

      dom.create('a', {
        class : 'export-to export-to-csv',
        innerHTML : 'Export CSV',
        onclick : function () {
          grid.exportToCSV();
        }
      }, wrapper);
    }
  });
});
