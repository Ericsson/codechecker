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
  'dojox/form/CheckedMultiSelect',
  'dojox/grid/DataGrid',
  'dijit/layout/ContentPane',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, ItemFileWriteStore, Deferred, all, Memory, Observable,
  CheckedMultiSelect, DataGrid, ContentPane, hashHelper, util) {

  function severityFormatter (severity) {
    var severity = util.severityFromCodeToString(severity);

    var title = severity.charAt(0).toUpperCase() + severity.slice(1);
    return '<span title="' + title  + '" class="customIcon icon-severity-'
      + severity + '"></span>';
  }

  var RunFilter = declare(CheckedMultiSelect, {
    _updateSelection: function() {
      this.inherited(arguments);
      if(this.dropDown && this.dropDownButton){
        var label = '';

        this.options.forEach(function(option) {
          if (option.selected)
            label += (label.length ? ', ' : '') + option.label;
        });

        this.dropDownButton.set('label', label.length ? label : this.label);
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
          that.dataGrid.refreshGrid(state);
          hashHelper.setStateValue('run', state);
        }
      });

      this.selectedRuns = null;
    },

    postCreate : function () {
      this.addChild(this._runFilter);

      var state = hashHelper.getValues();
      if (state.run)
        this.selectedRuns = state.run instanceof Array
          ? state.run.map(function (run) { return parseInt(run); })
          : [parseInt(state.run)];

      this.loadRunStoreData();
    },


    loadRunStoreData : function () {
      var that = this;

      CC_SERVICE.getRunData('', function (runs) {
        runs.sort(function (a, b) {
          if (a.name > b.name) return 1;
          if (a.name < b.name) return -1;

          return 0;
        }).forEach(function (run) {
          that._runStore.put({id : run.runId, label : run.name});
        });

        if (!that.selectedRuns)
          setTimeout(function () { that.dataGrid.refreshGrid(); }, 0);
        else
          that._runFilter.set('value', that.selectedRuns);
      });
    }
  });

  var CheckerStatistics = declare(DataGrid, {
    constructor : function () {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });

      this.structure = [
        { name : 'Checker', field : 'checker', width : '100%'},
        { name : 'Severity', field : 'severity', styles : 'text-align: center;', width : '15%', formatter : severityFormatter},
        { name : '<span class="customIcon detection-status-unresolved"></span> All reports', field : 'reports', width : '20%'},
        { name : '<span class="customIcon detection-status-resolved"></span> Resolved', field : 'resolved', width : '20%'},
        { name : '<span class="customIcon review-status-unreviewed"></span> Unreviewed', field : 'unreviewed', width : '20%'},
        { name : '<span class="customIcon review-status-confirmed-bug"></span>Confirmed bug', field : 'confirmed', width : '20%'},
        { name : '<span class="customIcon review-status-false-positive"></span> False positive', field : 'falsePositive', width : '20%'},
        { name : "<span class= \"customIcon review-status-wont-fix\"></span>Won't fix", field : 'wontFix', width : '20%'}
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;
      this.sortInfo = -2; // sort by severity
    },

    postCreate : function () {
      this.inherited(arguments);

      this._populateStatistics();
    },

    refreshGrid : function (runIds) {
      var that = this;

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
        {field : 'reviewStatus', values : [ReviewStatus.UNREVIEWED]},
        {field : 'reviewStatus', values : [ReviewStatus.CONFIRMED]},
        {field : 'reviewStatus', values : [ReviewStatus.FALSE_POSITIVE]},
        {field : 'reviewStatus', values : [ReviewStatus.WONT_FIX]},
        {field : 'detectionStatus', values : [DetectionStatus.RESOLVED]}
      ].map(function (q) {
        var that = this;

        var deferred = new Deferred();

        var reportFilter = new CC_OBJECTS.ReportFilter_v2();

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
            reports       : checkers[key].count ? checkers[key].count : '',
            unreviewed    : res[1][key] !== undefined ? res[1][key].count : '',
            confirmed     : res[2][key] !== undefined ? res[2][key].count : '',
            falsePositive : res[3][key] !== undefined ? res[3][key].count : '',
            wontFix       : res[4][key] !== undefined ? res[4][key].count : '',
            resolved      : res[5][key] !== undefined ? res[5][key].count : ''
          });
        });
        that.sort();
      });
    }
  });

  return declare(ContentPane, {
    constructor : function () {
      this._checkerStatistics = new CheckerStatistics();

      this._filterPane = new FilterPane({
        dataGrid : this._checkerStatistics
      });
    },

    postCreate : function () {
      this.addChild(this._filterPane);
      this.addChild(this._checkerStatistics);
    }
  });
});