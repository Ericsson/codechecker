// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/data/ItemFileWriteStore',
  'dojo/Deferred',
  'dojo/promise/all',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dojo/topic',
  'dojox/form/CheckedMultiSelect',
  'dojox/grid/DataGrid',
  'dojox/widget/Standby',
  'dijit/layout/ContentPane',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, ItemFileWriteStore, Deferred, all, Memory, Observable,
  topic, CheckedMultiSelect, DataGrid, Standby, ContentPane, hashHelper, util) {

  function severityFormatter(severity) {
    var severity = util.severityFromCodeToString(severity);

    var title = severity.charAt(0).toUpperCase() + severity.slice(1);
    return '<span title="' + title  + '" class="customIcon icon-severity-'
      + severity + '" style="cursor: pointer;"></span>';
  }

  function checkerNameFormatter(checkerName) {
    return '<span class="link">' + checkerName + '</span>';
  }

  function numberFormatter(num) {
    return !num ? '' : '<span class="link">' + num + '</span>';
  }

  var RunFilter = declare(CheckedMultiSelect, {
    _updateSelection: function() {
      this.inherited(arguments);

      if(this.dropDown && this.dropDownButton){
        var selectedOptions = this.options.filter(function (opt) {
          return opt.selected;
        });

        var label = selectedOptions.length ? selectedOptions.length == 1
            ? selectedOptions[0].label : "Multiple runs"
            : this.label;

        this.dropDownButton.set('label', label);
      }
    }
  });

  var FilterPane = declare(ContentPane, {
    constructor : function () {
      var that = this;

      this._runStore = new Observable(new Memory({}));

      this._runFilter = new RunFilter({
        store     : this._runStore,
        labelAttr : 'label',
        label     : "Get statistics only for runs...",
        multiple  : true,
        dropDown  : true,
        onChange  : function (state) {
          that.selectedRuns = state;
          this.changed = true;
        },
        onBlur : function () {
          if (!this.changed)
            return;

          var runIds = [];
          this.store.query({}).forEach(function (item) {
            if (that.selectedRuns.indexOf(item.label) !== -1)
              runIds.push(item.value);
          });

          that.dataGrid.refreshGrid(runIds);
          hashHelper.setStateValue('run', that.selectedRuns);
          this.changed = false;
        }
      });

      this.selectedRuns = null;
    },

    postCreate : function () {
      this.addChild(this._runFilter);

      var state = hashHelper.getValues();
      if (state.tab === 'statistics' && state.run)
        this.selectedRuns = state.run instanceof Array
          ? state.run.map(function (run) { return run; })
          : [state.run];
    },

    loadRunStoreData : function () {
      var that = this;

      CC_SERVICE.getRunData(null, function (runs) {
        runs.sort(function (a, b) {
          if (a.name > b.name) return 1;
          if (a.name < b.name) return -1;

          return 0;
        }).forEach(function (run) {
          that._runStore.put({
            id : run.name,
            label : run.name,
            value : run.runId
          });
        });

        if (that.selectedRuns)
          that._runFilter.set('value', that.selectedRuns);

        that.dataGrid.refreshGrid();
      });
    }
  });

  var CheckerStatistics = declare(DataGrid, {
    constructor : function (args) {
      dojo.safeMixin(this, args);

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
      this.escapeHTMLInData = false;
      this.sortInfo = -2; // sort by severity
    },

    onRowClick : function (evt) {
      var that = this;
      var item = this.getItem(evt.rowIndex);

      var runNameFilter = that.bugFilterView._runNameFilter;
      var checkerNameFilter = that.bugFilterView._checkerNameFilter;
      var reviewStatusFilter = that.bugFilterView._reviewStatusFilter;
      var detectionStatusFilter = that.bugFilterView._detectionStatusFilter;
      var severityFilter = that.bugFilterView._severityFilter;

      var state = that.bugFilterView.clearAll();
      state[checkerNameFilter.class] = item.checker;
      state[runNameFilter.class] = this.filterPane.selectedRuns;

      switch (evt.cell.field) {
        case 'checker':
          state[reviewStatusFilter.class] =
          Object.keys(CC_OBJECTS.ReviewStatus).map(function (key) {
            return reviewStatusFilter.stateConverter(
              CC_OBJECTS.ReviewStatus[key]);
          });

          state[detectionStatusFilter.class] =
          Object.keys(CC_OBJECTS.DetectionStatus).map(function (key) {
            return detectionStatusFilter.stateConverter(
              CC_OBJECTS.DetectionStatus[key]);
          });
          break;
        case 'severity':
          state[severityFilter.class] =
            severityFilter.stateConverter(item.severity[0]);
          break;
        case 'reports':
          // Show all reports
          break;
        case 'resolved':
          if (!item.resolved[0]) return;

          state[detectionStatusFilter.class] =
          detectionStatusFilter.stateConverter(
            CC_OBJECTS.DetectionStatus.RESOLVED);
          break;
        case 'unreviewed':
          if (!item.unreviewed[0]) return;

          state[reviewStatusFilter.class] = reviewStatusFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.UNREVIEWED);
          break;
        case 'confirmed':
          if (!item.confirmed[0]) return;

          state[reviewStatusFilter.class] = reviewStatusFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.CONFIRMED);
          break;
        case 'falsePositive':
          if (!item.falsePositive[0]) return;

          state[reviewStatusFilter.class] = reviewStatusFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.FALSE_POSITIVE);
          break;
        case 'intentional':
          if (!item.intentional[0]) return;

          state[reviewStatusFilter.class] = reviewStatusFilter.stateConverter(
            CC_OBJECTS.ReviewStatus.INTENTIONAL);
          break;
        default:
          return;
      }

      topic.publish('tab/allReports');
      topic.publish('filterchange', {
        parent : that.bugFilterView,
        changed : state
      });
    },

    refreshGrid : function (runIds) {
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

      this._populateStatistics(runIds);
    },

    _populateStatistics : function (runIds) {
      var that = this;

      var query = [
        {},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.UNREVIEWED]},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.CONFIRMED]},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.FALSE_POSITIVE]},
        {field : 'reviewStatus', values : [CC_OBJECTS.ReviewStatus.INTENTIONAL]},
        {field : 'detectionStatus', values : [CC_OBJECTS.DetectionStatus.RESOLVED]}
      ].map(function (q) {
        var that = this;

        var deferred = new Deferred();

        var reportFilter = new CC_OBJECTS.ReportFilter();
        reportFilter.isUnique = true;

        if (q.field)
          reportFilter[q.field] = q.values;

        CC_SERVICE.getCheckerCounts(runIds, reportFilter, null, function (res) {
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
    }
  });

  return declare(ContentPane, {
    postCreate : function () {
      this._standBy = new Standby({
        color : '#ffffff',
        target : this.domNode,
        duration : 0
      });
      this.addChild(this._standBy);

      this._checkerStatistics = new CheckerStatistics({
        bugFilterView : this.listOfAllReports._bugFilterView,
        standBy : this._standBy
      });

      this._filterPane = new FilterPane({
        dataGrid : this._checkerStatistics
      });

      this._checkerStatistics.set('filterPane', this._filterPane);

      this.addChild(this._filterPane);
      this.addChild(this._checkerStatistics);
    },

    onShow : function () {
      if (!this.initalized) {
        this.initalized = true;

        this._filterPane.loadRunStoreData();
      }
      hashHelper.resetStateValues({
        'tab' : 'statistics',
        'run' : this._filterPane.selectedRuns
      });
    }
  });
});
