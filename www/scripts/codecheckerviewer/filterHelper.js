// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dijit/form/Button',
  'dijit/layout/ContentPane',
  'codechecker/Filter'],
function (declare, Button, ContentPane, Filter) {
  /**
   * Transforms a ReportDataTypeCountList to a processable format.
   * The output format is:
   * {
   *   Infinity : { name : 'All', count : 20, checkers : {} },
   *   50       : { name : 'Critical', count : 10, checkers : { core.something : 5, unix.checker : 5 } },
   *   40       : ...
   *   ....     : ...
   * }
   * The keys of the returning object is the severity categories, and the
   * Infinity to contain the sum of all bugs. These keys are of course strings
   * and their order is not defined according to the JavaScript language.
   */
  function parseReportDataTypeCounts(reportDataTypeCountList) {
    var checkerInfo = { Infinity : { name : 'All', count : 0, checkers : {} } };

    for (var key in Severity)
      checkerInfo[Severity[key]] = {
        name : key[0] + key.slice(1).toLowerCase(),
        count : 0,
        checkers : {}
      };

    reportDataTypeCountList.forEach(function (e) {
      checkerInfo[e.severity].count += e.count;
      checkerInfo[e.severity].checkers[e.checkerId] = e.count;
      checkerInfo[Infinity].count += e.count;
    });

    return checkerInfo;
  }

  /**
   * This function gets the report type counts asynchronously and calls a
   * callback function which is passed an object that describes the values of
   * a Select dojo object.
   *
   * The function can be called with 4 or 5 arguments. In case of 4 arguments
   * a Filter object, a run, and the callback function has to be passed. In case
   * of 5 arguments two runs has to be passed in which case the diff result
   * types is computed.
   */
  function checkerInfoOptions() {
    if (arguments.length === 4) {
      var filter = arguments[0];
      var filterValues = arguments[1];
      var run1 = arguments[2];
      var cb = arguments[3];
    } else {
      var filter = arguments[0];
      var filterValues = arguments[1];
      var run1 = arguments[2];
      var run2 = arguments[3];
      var cb = arguments[4];
    }

    var checkerToSelect = 'all';
    if( filterValues ){
      checkerToSelect = filterValues.checker;
      // query all but only select which was on the filter url!!!!!
      filterValues.checker = '';
    }

    function result(runResultTypes) {

      var checkerInfo = parseReportDataTypeCounts(runResultTypes);
      var selectOptions = [{
        label : checkerInfo.Infinity.name
          + ' (' + checkerInfo.Infinity.count + ')',
        value : 'all'
      }];

      var severities = [];
      for (var key in Severity)
        severities.push({ key : key, value : Severity[key] });

      severities.sort(function (a, b) { return b.value - a.value; })
      .forEach(function (severity) {
        var item = checkerInfo[severity.value];
        if (item.count > 0) {
          selectOptions.push({
            label : item.name + ' (' + item.count + ')',
            value : 'severity#' + severity.value,
            selected : 'severity#' + severity.value === checkerToSelect
          });

          for (var checkerKey in item.checkers){
            var val = 'checker#' + checkerKey;
            var sel = val === checkerToSelect;
            selectOptions.push({
              label : '&nbsp;&nbsp;&nbsp;&nbsp;' + checkerKey
                + ' (' + item.checkers[checkerKey] + ')',
              value : val,
              selected : sel
            });
          }

        }
      });

      cb(selectOptions);
    }

    // Construct a filter to get the number of results for the
    // checker select part of the filter on the UI.
    var reportFilter = module.filterToReportFilter(filter, filterValues);

    if (arguments.length === 4) {
      CC_SERVICE.getRunResultTypes( run1, [reportFilter], result);
    }
    else {

      // Compare UI values to the provided filter values, if they are different
      // use the UI values to filter.
      // UI values might be empty on page load!
      var uiValues = filter.getValues()
      var difftype = filterValues ? filterValues.difftype : 'new';

      if (uiValues.difftype !== difftype && uiValues.difftype) {
        difftype = uiValues.difftype;
      }

      switch (difftype) {
        case 'new':        difftype = CC_OBJECTS.DiffType.NEW;        break;
        case 'resolved':   difftype = CC_OBJECTS.DiffType.RESOLVED;   break;
        case 'unresolved': difftype = CC_OBJECTS.DiffType.UNRESOLVED; break;
      }

      CC_SERVICE.getDiffResultTypes( run1, run2, difftype, [reportFilter],
                                     result);
    }
  }

  /**
   * Add path field and set to the value.
   */
  function addPathFilterField(filter, value) {
    filter.addField('text', 'path', 'Path filter', value);
  }

  /**
   * Register the callbacks for the checker filter fields.
   */
  function addCheckerIndexField(filter, filterValues, run1, run2) {
    var callback
      = arguments.length === 3
      ? function (cb) { return checkerInfoOptions(filter, filterValues, run1, cb); }
      : function (cb) { return checkerInfoOptions(filter, filterValues, run1, run2, cb); }
    filter.addField('select', 'checker', callback);
  }

  /**
   * Set the diff type filter field.
   */
  function addDiffTypeField(filter, selected_value) {
    var options = [
      { label : 'New only',   value : 'new'        },
      { label : 'Resolved',   value : 'resolved', selected: 'resolved' === selected_value },
      { label : 'Unresolved', value : 'unresolved', selected: 'unresolved' === selected_value}
    ];

    filter.addField('select', 'difftype', options);
  }

  /**
   * Create a filter group which can contain multiple filters.
   */
  var FilterGroup = declare(ContentPane, {
    constructor : function (filters) {
      this.style = 'padding: 5px';
    },

    postCreate : function () {
        filters = this.filters;
        if ( !filters ) {
          this._addPlusButton(this._addFilter());
        } else {
          this._addPlusButton(this._addFilter(filters[0]));
          for (i = 1; i < filters.length; i++) {
            this._addMinusButton(this._addFilter(filters[i]));
          }
        }
    },

    _addFilter : function (filterValue) {
      var that = this;

      var filter
        = this.runId
        ? module.createOverviewFilter(this.runId, filterValue)
        : module.createDiffOverviewFilter(this.baselineId, this.newcheckId, filterValue);

      filter.onChange = function () {
        var allValues = [];
        that.getChildren().forEach(function (filter) {
          allValues.push(filter.getValues());
        });
        that.onChange(allValues);
      };

      this.addChild(filter);
      return filter;
    },

    _addPlusButton : function (filter) {
      var that = this;
      filter.addChild(new Button({
        iconClass : 'plusIcon',
        showLabel : false,
        onClick : function () {
          var newFilter = that._addFilter();
          that._addMinusButton(newFilter);
          that.onAddFilter(newFilter);
        }
      }));
    },

    _addMinusButton : function (filter) {
      var that = this;
      filter.addChild(new Button({
        iconClass : 'minusIcon',
        showLabel : false,
        onClick : function () {
          that.removeChild(filter);
          that.onRemoveFilter(filter);
        }
      }));
    },

    onAddFilter : function (filter) {},
    onRemoveFilter : function (filter) {},
    onChange : function (allValues) {}
  });

  var module = {
    /**
     * Construct and initialize a filter.
     */
    createOverviewFilter : function (runId, filterValue) {
      var filter = new Filter();
      if ( filterValue === undefined ){
        addPathFilterField(filter, '');
        // Needs all the filter values to calculate the checker filter field.
        addCheckerIndexField(filter, filterValue, runId);
      } else {
        addPathFilterField(filter, filterValue.path);
        // Needs all the filter values to calculate the checker filter field.
        addCheckerIndexField(filter, filterValue, runId);
      }
      return filter;
    },

    /**
     * Construct and initialize a diff filter.
     */
    createDiffOverviewFilter : function (baselineId, newcheckId, filterValue) {
      filter = new Filter();

      if ( !filterValue ){
        addPathFilterField(filter, '');
        addDiffTypeField(filter);
        // Needs all the filter values to calculate the checker filter field.
        addCheckerIndexField(filter, filterValue, baselineId, newcheckId);
      } else {
        addPathFilterField(filter, filterValue.path);
        addDiffTypeField(filter, filterValue.difftype);
        // Needs all the filter values to calculate the checker filter field.
        addCheckerIndexField(filter, filterValue, baselineId, newcheckId);
      }
      return filter;
    },

    /**
     * This function converts an object of type Filter (created earlier by
     * createOverviewFilter()) to ReportFilter thrift object.
     */
    filterToReportFilter : function (filter, fv) {
      var reportFilter = new CC_OBJECTS.ReportFilter();

      if ( !fv ){
        // Setup default values for the report filter.
        reportFilter.filepath = '**';
        reportFilter.suppressed = false;
        reportFilter.checkerId = null;
        reportFilter.severity = null;
      }
      else {
        var uiValues = filter.getValues();

        // Compare UI values to the provided filter values, if they are different
        // use the UI values to filter.
        // UI values might be empty on page load!
        if (uiValues.suppression === fv.suppression || !uiValues.suppression) {
          reportFilter.suppressed = fv.suppression === 'supp';
        } else {
          reportFilter.suppressed = uiValues.suppression === 'supp';
        }

        reportFilter.filepath = '*' +
          (uiValues.filepath === fv.filepath ? fv.path : uiValues.path) + '*';

        if (fv.checker === 'all'){
          reportFilter.checkerId = null;
        } else {
          // The filter checker value is not all it can be a severity level
          // or a concrete checker.
          var index = fv.checker.indexOf('#');
          var type = fv.checker.substr(0, index);
          var value = fv.checker.substr(index + 1);

          switch (type) {
            case 'severity': reportFilter.severity = parseInt(value); break;
            case 'checker': reportFilter.checkerId = value; break;
          }
        }
      }

      return reportFilter;
    },

    filterGroupToReportFilters : function (filterGroup, filters) {
      var that = this;

      var allReportFilters = [];
      filterGroup.getChildren().forEach(function (filter, i) {
        if( !filters){
          allReportFilters.push(that.filterToReportFilter(filter));
        }
        else{
          allReportFilters.push(that.filterToReportFilter(filter, filters[i]));
        }
      });

      return allReportFilters;
    },

    FilterGroup : FilterGroup
  };

  return module;
});
