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
   * The function can be called with 3 or 4 arguments. In case of 3 arguments
   * a Filter object, a run, and the callback function has to be passed. In case
   * of 4 arguments two runs has to be passed in which case the diff result
   * types is computed.
   */
  function checkerInfoOptions() {
    if (arguments.length === 3) {
      var filter = arguments[0];
      var run1 = arguments[1];
      var cb = arguments[2];
    } else {
      var filter = arguments[0];
      var run1 = arguments[1];
      var run2 = arguments[2];
      var cb = arguments[3];
    }

    function result(runResultTypes) {
      var checkerInfo = parseReportDataTypeCounts(runResultTypes);

      var selectOptions = [{
        label : checkerInfo.Infinity.name
          + ' (' + checkerInfo.Infinity.count + ')',
        value : 'all'
      }];

      for (var key in Severity) {
        var item = checkerInfo[Severity[key]];

        if (item.count > 0) {
          selectOptions.push({
            label : item.name + ' (' + item.count + ')',
            value : 'severity#' + Severity[key]
          });

          for (var checkerKey in item.checkers)
            selectOptions.push({
              label : '&nbsp;&nbsp;&nbsp;&nbsp;' + checkerKey
                + ' (' + item.checkers[checkerKey] + ')',
              value : 'checker#' + checkerKey
            });
        }
      }

      cb(selectOptions);
    }

    var reportFilter = module.filterToReportFilter(filter);

    var difftype;
    switch (filter.getValue('difftype')) {
      case 'new':        difftype = CC_OBJECTS.DiffType.NEW;        break;
      case 'resolved':   difftype = CC_OBJECTS.DiffType.RESOLVED;   break;
      case 'unresolved': difftype = CC_OBJECTS.DiffType.UNRESOLVED; break;
    }

    if (arguments.length === 3) {
      CC_SERVICE.getRunResultTypes(
        run1,
        [reportFilter],
        result);
    }
    else
      CC_SERVICE.getDiffResultTypes(
        run1,
        run2,
        difftype,
        [reportFilter],
        result);
  }

  function addPathFilterField(filter) {
    filter.addField('text', 'path', 'Path filter');
  }

  function addSuppressionStateField(filter) {
    filter.addField('select', 'suppression', [
      { label : 'Unsuppressed', value : 'unsup' },
      { label : 'Suppressed',   value : 'supp'  }
    ]);
  }

  function addCheckerIndexField(filter, run1, run2) {
    var callback
      = arguments.length === 2
      ? function (cb) { return checkerInfoOptions(filter, run1, cb); }
      : function (cb) { return checkerInfoOptions(filter, run1, run2, cb); }

    filter.addField('select', 'checker', callback);
  }

  function addDiffTypeField(filter) {
    filter.addField('select', 'difftype', [
      { label : 'New only',   value : 'new'        },
      { label : 'Resolved',   value : 'resolved'   },
      { label : 'Unresolved', value : 'unresolved' }
    ]);
  }

  var FilterGroup = declare(ContentPane, {
    constructor : function () {
      this.style = 'padding: 5px';
    },

    postCreate : function () {
      this._addPlusButton(this._addFilter());
    },

    _addFilter : function () {
      var that = this;

      var filter
        = this.runId
        ? module.createOverviewFilter(this.runId)
        : module.createDiffOverviewFilter(this.baselineId, this.newcheckId);

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
    createOverviewFilter : function (runId) {
      var filter = new Filter();

      addPathFilterField(filter);
      addSuppressionStateField(filter);
      addCheckerIndexField(filter, runId);

      return filter;
    },

    createDiffOverviewFilter : function (baselineId, newcheckId) {
      filter = new Filter();

      addPathFilterField(filter);
      addSuppressionStateField(filter);
      addDiffTypeField(filter);
      addCheckerIndexField(filter, baselineId, newcheckId);

      return filter;
    },

    /**
     * This function converts an object of type Filter (created earlier by
     * createOverviewFilter()) to ReportFilter thrift object.
     */
    filterToReportFilter : function (filter) {
      var reportFilter = new CC_OBJECTS.ReportFilter();
      var filterValues = filter.getValues();
      
      if (!filterValues.checker)
        filterValues.checker = '';

      reportFilter.filepath = '*' + filterValues.path + '*';
      reportFilter.suppressed = filterValues.suppression === 'supp';

      var index = filterValues.checker.indexOf('#');
      var type = filterValues.checker.substr(0, index);
      var value = filterValues.checker.substr(index + 1);

      switch (type) {
        case 'severity': reportFilter.severity = parseInt(value); break;
        case 'checker': reportFilter.checkerId = value; break;
      }

      return reportFilter;
    },

    filterGroupToReportFilters : function (filterGroup) {
      var that = this;

      var allReportFilters = [];
      filterGroup.getChildren().forEach(function (filter) {
        allReportFilters.push(that.filterToReportFilter(filter));
      });

      return allReportFilters;
    },

    FilterGroup : FilterGroup
  };

  return module;
});
