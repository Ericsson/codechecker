// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/_base/lang',
  'dojo/dom-construct',
  'dijit/form/Button',
  'codechecker/hashHelper',
  'codechecker/filter/BugFilterView',
  'codechecker/filter/BugPathLengthFilter',
  'codechecker/filter/CheckerMessageFilter',
  'codechecker/filter/CheckerNameFilter',
  'codechecker/filter/DateFilter',
  'codechecker/filter/DetectionStatusFilter',
  'codechecker/filter/FileFilter',
  'codechecker/filter/ReportCount',
  'codechecker/filter/RunBaseFilter',
  'codechecker/filter/RunHistoryTagFilter',
  'codechecker/filter/SeverityFilter',
  'codechecker/filter/SourceComponentFilter',
  'codechecker/filter/UniqueFilter'],
function (declare, lang, dom, Button, hashHelper, BugFilterView,
  BugPathLengthFilter, CheckerMessageFilter, CheckerNameFilter, DateFilter,
  DetectionStatusFilter, FileFilter, ReportCount, RunBaseFilter,
  RunHistoryTagFilter, SeverityFilter, SourceComponentFilter, UniqueFilter) {

  return declare(BugFilterView, {
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
        defaultValue : true,
        defaultValues : function () {
          var state = {};
          state[this.class] = this.defaultValue ? 'on' : 'off';
          return state;
        },
        updateReportFilter : function (isUnique) {
          that.reportFilter.isUnique = isUnique;

          if (isUnique)
            that._detectionStatusFilter.notAvailable();
          else
            that._detectionStatusFilter.available();
        }
      });
      this.register(this._uniqueFilter);
      this.addChild(this._uniqueFilter);

      //--- Report count ---//

      this._reportCount = new ReportCount({
        parent : this,
        class : 'report-count'
      });
      this.register(this._reportCount);
      this.addChild(this._reportCount);

      //--- Run base line filter ---//

      this._runBaseLineFilter = new RunBaseFilter({
        class : 'run',
        title : 'Run name',
        parent : this,
        updateReportFilter : function () {
          that.runIds = this.getRunIds();
        },
        initReportFilterOptions : function (opt) {
          return that.initReportFilterOptions(opt);
        }
      });
      this.register(this._runBaseLineFilter);
      this.addChild(this._runBaseLineFilter);

      //--- Run history tags filter ---//

      this._runHistoryTagFilter = new RunHistoryTagFilter({
        class : 'run-tag',
        title : 'Run tag',
        parent   : this,
        updateReportFilter : function () {
          that.reportFilter.runTag = this.getTagIds();
        },
        initReportFilterOptions : function (opt) {
          return that.initReportFilterOptions(opt);
        }
      });
      this.register(this._runHistoryTagFilter);
      this.addChild(this._runHistoryTagFilter);

      //--- Detection status filter ---//

      this._detectionStatusFilter = new DetectionStatusFilter({
        class : 'detection-status',
        title : 'Detection status',
        parent   : this,
        updateReportFilter : function (detectionStatuses) {
          that.reportFilter.detectionStatus = detectionStatuses;
        }
      });
      this.register(this._detectionStatusFilter);
      this.addChild(this._detectionStatusFilter);

      //--- Severity filter ---//

      this._severityFilter = new SeverityFilter({
        class : 'severity',
        title : 'Severity',
        parent   : this,
        updateReportFilter : function (severities) {
          that.reportFilter.severity = severities;
        }
      });
      this.register(this._severityFilter);
      this.addChild(this._severityFilter);

      //--- Bug path length filter ---//

      this._bugPathLengthFilter = new BugPathLengthFilter({
        class : 'bug-path-length',
        title : 'Bug path length',
        parent   : this,
        updateReportFilter : function (state) {
          var bugPathLength = null;

          if (state.minBugPathLength || state.maxBugPathLength)  {
            bugPathLength = new CC_OBJECTS.BugPathLengthRange({
              min : state.minBugPathLength ? state.minBugPathLength : null,
              max : state.maxBugPathLength ? state.maxBugPathLength : null,
            });
          }

          that.reportFilter.bugPathLength = bugPathLength;
        },
      });
      this.register(this._bugPathLengthFilter);
      this.addChild(this._bugPathLengthFilter);

      //--- Detection date filter ---//

      this._detectionDateFilter = new DateFilter({
        class    : 'detection-date',
        title    : 'Detection date',
        parent   : this,
        updateReportFilter : function (state) {
          that.reportFilter.firstDetectionDate = state.detectionDate;
          that.reportFilter.fixDate = state.fixDate;
        }
      });
      this.register(this._detectionDateFilter);
      this.addChild(this._detectionDateFilter);

      //--- File filter ---//

      this._fileFilter = new FileFilter({
        class : 'filepath',
        title : 'File path',
        parent: this,
        updateReportFilter : function (files) {
          that.reportFilter.filepath = files;
        }
      });
      this.register(this._fileFilter);
      this.addChild(this._fileFilter);

      // --- Source component filter ---//

      this._sourceComponentFilter = new SourceComponentFilter({
        class : 'source-component',
        title : 'Source component',
        parent: this,
        updateReportFilter : function (components) {
          that.reportFilter.componentNames = components;
        }
      });
      this.register(this._sourceComponentFilter);
      this.addChild(this._sourceComponentFilter);

      //--- Checker name filter ---//

      this._checkerNameFilter = new CheckerNameFilter({
        class : 'checker-name',
        title : 'Checker name',
        parent: this,
        updateReportFilter : function (checkerNames) {
          that.reportFilter.checkerName = checkerNames;
        }
      });
      this.register(this._checkerNameFilter);
      this.addChild(this._checkerNameFilter);

      //--- Checker message filter ---//

      this._checkerMessageFilter = new CheckerMessageFilter({
        class : 'checker-msg',
        title : 'Checker message',
        parent   : this,
        updateReportFilter : function (checkerMessages) {
          that.reportFilter.checkerMsg = checkerMessages;
        }
      });
      this.register(this._checkerMessageFilter);
      this.addChild(this._checkerMessageFilter);

      // Initalize only the current tab.
      var queryParams = hashHelper.getState();

      if (this.parent.tab === queryParams.tab)
        this.initAll(queryParams);

      this._subscribeTopics();
    }
  });
});
