// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojo/Deferred',
  'dojo/dom-construct',
  'dojo/topic',
  'dijit/form/Button',
  'dijit/layout/ContentPane',
  'codechecker/hashHelper',
  'codechecker/filter/DateFilter',
  'codechecker/filter/DiffTypeFilter',
  'codechecker/filter/ReportCount',
  'codechecker/filter/RunBaseFilter',
  'codechecker/filter/RunHistoryTagFilter',
  'codechecker/filter/SelectFilter',
  'codechecker/filter/UniqueFilter',
  'codechecker/util'],
function (declare, lang, Deferred, dom, topic, Button, ContentPane, hashHelper,
  DateFilter, DiffTypeFilter, ReportCount, RunBaseFilter, RunHistoryTagFilter,
  SelectFilter, UniqueFilter, util) {

  // Global variables which will store common filter options.
  var runIds = [];
  var reportFilter = null;
  var cmpData = null;

  return declare(ContentPane, {
    constructor : function () {
      this._filters = []; // Registered filter components.
      this._isInitalized = false; // Shows that filter is already initalized.
      reportFilter = new CC_OBJECTS.ReportFilter();
    },

    postCreate : function () {
      var that = this;

      //--- Clear all filter button ---//

      this._topBarPane = dom.create('div', { class : 'top-bar'}, this.domNode);
      this._clearAllButton = new Button({
        class   : 'clear-all-btn',
        label   : 'Clear All Filters',
        onClick : function () {
          that.clearAll();
          that.notifyAll();
        }
      }, this._topBarPane);

      //--- Unique reports filter ---//

      this._uniqueFilter = new UniqueFilter({
        class : 'is-unique',
        parent : this,
        updateReportFilter : function (isUnique) {
          reportFilter.isUnique = isUnique;
        }
      });
      this.register(this._uniqueFilter);
      this.addChild(this._uniqueFilter);

      //--- Report count ---//

      this._reportCount = new ReportCount({
        parent : this
      });
      this.register(this._reportCount);
      this.addChild(this._reportCount);

      //--- Run filter ---//

      if (this.diffView) {
        cmpData = new CC_OBJECTS.CompareData();

        //--- Run baseline filter ---//

        this._runBaseLineFilter = new RunBaseFilter({
          class : 'baseline',
          title : 'Baseline',
          parent : this,
          updateReportFilter : function () {
            runIds = this.getRunIds();
          }
        });
        this.register(this._runBaseLineFilter);
        this.addChild(this._runBaseLineFilter);

        //--- Run base filter ---//

        this._runNewCheckFilter = new RunBaseFilter({
          class : 'newcheck',
          title : 'Newcheck',
          parent : this,
          updateReportFilter : function () {
            cmpData.runIds = this.getRunIds();
          }
        });
        this.register(this._runNewCheckFilter);
        this.addChild(this._runNewCheckFilter);

        //--- Diff type filter ---//

        this._diffTypeFilter = new DiffTypeFilter({
          class : 'difftype',
          title : 'Diff type',
          parent : this,
          updateReportFilter : function (diffType) {
            cmpData.diffType = diffType;
          }
        });
        this.register(this._diffTypeFilter);
        this.addChild(this._diffTypeFilter);
      } else {
        this._runNameFilter = new RunBaseFilter({
          class : 'run',
          title : 'Run name',
          parent : this,
          updateReportFilter : function () {
            runIds = this.getRunIds();
          }
        });
        this.register(this._runNameFilter);
        this.addChild(this._runNameFilter);
      }

      //--- Review status filter ---//

      this._reviewStatusFilter = new SelectFilter({
        class : 'review-status',
        title : 'Review status',
        parent   : this,
        updateReportFilter : function (reviewStatuses) {
          reportFilter.reviewStatus = reviewStatuses;
        },
        stateConverter : function (value) {
          var status = util.enumValueToKey(
            CC_OBJECTS.ReviewStatus, parseInt(value)).replace('_', ' ');
          return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
        },
        stateDecoder : function (key) {
          return CC_OBJECTS.ReviewStatus[key.replace(' ', '_').toUpperCase()];
        },
        getIconClass : function (value) {
          var statusCode = this.stateDecoder(value);
          return 'customIcon ' + util.reviewStatusCssClass(statusCode);
        },
        getItems : function (opt) {
          opt = that.initReportFilterOptions(opt);
          opt.reportFilter.reviewStatus = null;

          var deferred = new Deferred();
          CC_SERVICE.getReviewStatusCounts(opt.runIds, opt.reportFilter,
          opt.cmpData, function (res) {
            deferred.resolve(Object.keys(CC_OBJECTS.ReviewStatus).map(
              function (key) {
                var value = CC_OBJECTS.ReviewStatus[key];
                return {
                  value : util.reviewStatusFromCodeToString(value),
                  count : res[value] !== undefined ? res[value] : 0
                };
            }));
          });
          return deferred;
        }
      });
      this.register(this._reviewStatusFilter);
      this.addChild(this._reviewStatusFilter);

      //--- Detection status filter ---//

      this._detectionStatusFilter = new SelectFilter({
        class : 'detection-status',
        title : 'Detection status',
        parent   : this,
        updateReportFilter : function (detectionStatuses) {
          reportFilter.detectionStatus = detectionStatuses;
        },
        stateConverter : function (value) {
          var status = util.enumValueToKey(
            CC_OBJECTS.DetectionStatus, parseInt(value));
          return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
        },
        stateDecoder : function (key) {
          return CC_OBJECTS.DetectionStatus[key.toUpperCase()];
        },
        getIconClass : function (value) {
          return 'customIcon detection-status-' + value.toLowerCase();
        },
        getItems : function (opt) {
          opt = that.initReportFilterOptions(opt);
          opt.reportFilter.detectionStatus = null;

          var deferred = new Deferred();
          CC_SERVICE.getDetectionStatusCounts(opt.runIds, opt.reportFilter,
          opt.cmpData, function (res) {
            deferred.resolve(Object.keys(CC_OBJECTS.DetectionStatus).map(
              function (key) {
                var value = CC_OBJECTS.DetectionStatus[key];
                return {
                  value : util.detectionStatusFromCodeToString(value),
                  count : res[value] !== undefined ? res[value] : 0
                };
            }));
          });
          return deferred;
        }
      });
      this.register(this._detectionStatusFilter);
      this.addChild(this._detectionStatusFilter);

      //--- Severity filter ---//

      this._severityFilter = new SelectFilter({
        class : 'severity',
        title : 'Severity',
        parent   : this,
        updateReportFilter : function (severities) {
          reportFilter.severity = severities;
        },
        stateConverter : function (value) {
          var status = util.enumValueToKey(
            CC_OBJECTS.Severity, parseInt(value));
          return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
        },
        stateDecoder : function (key) {
          return CC_OBJECTS.Severity[key.toUpperCase()];
        },
        getIconClass : function (value) {
          return 'customIcon icon-severity-' + value.toLowerCase();
        },
        getItems : function (opt) {
          opt = that.initReportFilterOptions(opt);
          opt.reportFilter.severity = null;

          var deferred = new Deferred();
          CC_SERVICE.getSeverityCounts(opt.runIds, opt.reportFilter,
          opt.cmpData, function (res) {
            deferred.resolve(Object.keys(CC_OBJECTS.Severity).sort(
              function (a, b) {
                return CC_OBJECTS.Severity[a] < CC_OBJECTS.Severity[b];
              }).map(function (key) {
                var value = CC_OBJECTS.Severity[key];
                return {
                  value : key[0] + key.slice(1).toLowerCase(),
                  count : res[value] !== undefined ? res[value] : 0
                };
              }));
          });

          return deferred;
        }
      });
      this.register(this._severityFilter);
      this.addChild(this._severityFilter);

      //--- Run history tags filter ---//

      this._runHistoryTagFilter = new RunHistoryTagFilter({
        class : 'run-tag',
        title : 'Run tag',
        parent   : this,
        updateReportFilter : function () {
          reportFilter.runTag = this.getTagIds();
        }
      });
      this.register(this._runHistoryTagFilter);
      this.addChild(this._runHistoryTagFilter);

      //--- Detection date filter ---//

      this._detectionDateFilter = new DateFilter({
        class    : 'detection-date',
        title    : 'Detection date',
        parent   : this,
        updateReportFilter : function (state) {
          reportFilter.firstDetectionDate = state.detectionDate;
          reportFilter.fixDate = state.fixDate;
        }
      });
      this.register(this._detectionDateFilter);
      this.addChild(this._detectionDateFilter);

      //--- File filter ---//

      this._fileFilter = new SelectFilter({
        class : 'filepath',
        title : 'File',
        parent: this,
        search : {
          enable : true,
          serverSide : true,
          regex : true,
          placeHolder : 'Search for files...'
        },
        labelFormatter : function (label) {
          return '&lrm;' + label + '&lrm;';
        },
        updateReportFilter : function (files) {
          reportFilter.filepath = files;
        },
        getItems : function (opt) {
          opt = that.initReportFilterOptions(opt);
          opt.reportFilter.filepath = opt.query ? opt.query : null;

          var deferred = new Deferred();
          CC_SERVICE.getFileCounts(opt.runIds, opt.reportFilter,
          opt.cmpData, opt.limit, opt.offset, function (res) {
            // Order the results alphabetically.
            deferred.resolve(Object.keys(res).sort(function (a, b) {
                if (a < b) return -1;
                if (a > b) return 1;
                return 0;
            }).map(function (file) {
              return {
                value : file,
                count : res[file]
              };
            }));
          });
          return deferred;
        }
      });
      this.register(this._fileFilter);
      this.addChild(this._fileFilter);

      //--- Checker name filter ---//

      this._checkerNameFilter = new SelectFilter({
        class : 'checker-name',
        title : 'Checker name',
        parent: this,
        search : {
          enable : true,
          placeHolder : 'Search for checker names...'
        },
        updateReportFilter : function (checkerNames) {
          reportFilter.checkerName = checkerNames;
        },
        getItems : function (opt) {
          opt = that.initReportFilterOptions(opt);
          opt.reportFilter.checkerName = opt.query ? opt.query : null;

          var deferred = new Deferred();
          CC_SERVICE.getCheckerCounts(opt.runIds, opt.reportFilter,
          opt.cmpData, opt.limit, opt.offset, function (res) {
            deferred.resolve(res.map(function (checker) {
              return {
                value : checker.name,
                count : checker.count
              };
            }));
          });
          return deferred;
        }
      });
      this.register(this._checkerNameFilter);
      this.addChild(this._checkerNameFilter);

      //--- Checker message filter ---//

      this._checkerMessageFilter = new SelectFilter({
        class : 'checker-msg',
        title : 'Checker message',
        parent   : this,
        search : {
          enable : true,
          serverSide : true,
          regex : true,
          placeHolder : 'Search for checker messages...'
        },
        updateReportFilter : function (checkerMessages) {
          reportFilter.checkerMsg = checkerMessages;
        },
        getItems : function (opt) {
          opt = that.initReportFilterOptions(opt);
          opt.reportFilter.checkerMsg = opt.query ? opt.query : null;

          if (opt.selected)
            opt.reportFilter.checkerMsg = opt.selected;

          var deferred = new Deferred();
          CC_SERVICE.getCheckerMsgCounts(opt.runIds, opt.reportFilter,
          opt.cmpData, opt.limit, opt.offset, function (res) {
            deferred.resolve(Object.keys(res).map(function (msg) {
              return {
                value : msg,
                count : res[msg]
              };
            }));
          });
          return deferred;
        }
      });
      this.register(this._checkerMessageFilter);
      this.addChild(this._checkerMessageFilter);

      //--- Initalize registered filters by URL ---//

      var queryParams = hashHelper.getState();

      // Initalize only the current tab.
      if (this.parent.tab === queryParams.tab)
        this.initAll(queryParams);

      this._subscribeTopics();
    },

    // Subscribe on topics
    _subscribeTopics : function () {
      var that = this;

      // When "browser back" or "browser forward" button is pressed we update
      // the filter by the url state.
      that._hashChangeTopic = topic.subscribe('/dojo/hashchange',
      function (url) {
        if (!that.parent.selected || hashHelper.hashSetProgress)
          return;

        var state = hashHelper.getState();
        that.initAll(state);
      });
    },

    // Returns report filter options of the current filter set.
    getReportFilter : function () { return reportFilter; },

    // Returns run ids of the current filter set.
    getRunIds : function () { return runIds; },

    // It will return null if filter view is normal otherwise in diff view
    // it returns filter compare data of the current filter set.
    getCmpData : function () { return cmpData; },

    // Register a new filter component.
    register : function (filter) { this._filters.push(filter); },

    // Returns true if the filter view is already initalized otherwise false.
    // Filter view is being initalized when it will be shown first.
    isInitalized : function () { return this._isInitalized; },

    // Returns copy of report filter options.
    initReportFilterOptions : function (opt) {
      if (!opt) opt = {};
      if (!opt.runIds) opt.runIds = lang.clone(runIds);
      if (!opt.reportFilter) opt.reportFilter = lang.clone(reportFilter);
      if (!opt.cmpData) opt.cmpData = lang.clone(cmpData);
      if (!opt.offset) opt.offset = 0;
      return opt;
    },

    // Return the URL state of the current filter set.
    getUrlState : function () {
      var state = {};
      this._filters.forEach(function (filter) {
        var urlState = filter.getUrlState();
        if (urlState)
          Object.keys(urlState).forEach(function(key) {
            state[key] = urlState[key];
          });
      });
      return state;
    },

    // Initalize all filter by URL parameters.
    initAll : function (queryParams) {
      if (!queryParams) queryParams = {};

      this._filters.forEach(function (filter) {
        filter.initByUrl(queryParams);
      });

      //--- Notify all filters on changed ---//

      this.notifyAll();
      this._isInitalized = true;
    },

    // Notify all filter except those which are in the except array parameter.
    notifyAll : function (except) {
      this._filters.forEach(function (filter) {
        if (!except || except.indexOf(filter) === -1)
          filter.notify();
      });

      //--- Update URL state ---//

      var state = this.getUrlState();
      hashHelper.setStateValues(state);
    },

    // Clears all filter.
    clearAll() {
      this._filters.forEach(function (filter) {
        filter.clear();
      });
    },

    // Destroy DOM elements and subscriptions.
    destroy : function () {
      this.inherited(arguments);
      this._hashChangeTopic.remove();
    }
  });
});
