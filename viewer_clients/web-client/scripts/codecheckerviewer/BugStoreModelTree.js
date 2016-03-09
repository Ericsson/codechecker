// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/store/Memory",
  "dojo/store/Observable",
  "dijit/tree/ObjectStoreModel",
  "dijit/Tooltip",
  "scripts/codecheckerviewer/HtmlTree.js",
], function (declare, Memory, Observable, ObjectStoreModel, Tooltip, HtmlTree) {

  /**
   * Contains the bug tree (with steps) for a specified file.
   * Encapsulates the 3 parts of a Dojo Tree: the Store, the Model and the Tree
   * objects.
   */

return declare(null, {


  /**
   * Construct a new object. The following arguments are required:
   *   runId: a run id
   *   fileId: the file's id
   *   filePath: the files's path
   */
  constructor : function (args) {
    var that = this;
    declare.safeMixin(that, args);

    that.bugStore = new Observable(new Memory({
      data : [
        {
          id     : "root"
        },
        {
          name   : "Loading bugs...",
          id     : "unspecified",
          parent : "root",
          isLeaf : true
        }
      ],
      getChildren : function (node) {
        return this.query({ parent: node.id });
      }
    }));

    that.bugModel = new ObjectStoreModel({
      store : that.bugStore,
      query : { id : "root" },
      mayHaveChildren: function (item){
        return (item.isLeaf === false);
      }
    });

    that.bugTree = new HtmlTree({
      region       : "left",
      splitter     : true,
      model        : that.bugModel,
      openOnClick  : true,
      showRoot     : false,
      getIconClass : function (item, opened) {
        if (item.isLeaf === false) {
          if (opened) {
            return "dijitFolderOpened";
          } else {
            return "dijitFolderClosed";
          }
        } else {
          return "";
        }
      },
      _onNodeMouseEnter : function (node, evt) {
        if (node.item.isLeaf === true) {
          Tooltip.show(node.item.name, node.domNode, ['above']);
        }
      },
      _onNodeMouseLeave : function (node, evt) {
        if (node.item.isLeaf === true) {
          Tooltip.hide(node.domNode);
        }
      }
    });

    that.loadBugStoreData();
  },


  /**
   * Queries run results for the file. The given onComplete callback function
   * will be called with the result array as argument. On error it logs the
   * error and calls onComplete with an empty array.
   *
   * This method is asynchronous.
   *
   * @param onComplete a callback function for the results.
   */
  _queryReportsForFile : function (onComplete) {
    var that = this;

    var limit = codeCheckerDBAccess.MAX_QUERY_SIZE;
    var filter = new codeCheckerDBAccess.ReportFilter();
    filter.filepath = that.filePath;

    CC_SERVICE.getRunResults(that.runId, limit, 0, [], [filter], function (result) {
      if (result instanceof RequestFailed) {
        console.error("Failed to load run results for "+ that.filePath, result);
        onComplete([]);
      } else {
        onComplete(result);
      }
    });
  },


  /**
   * Builds the execution path for the given report and adds it to the bug
   * store. It calls onComplete at the end of the process with no parameters.
   *
   * This method is asynchronous.
   *
   * @param bugStore a bug store for storing new tree nodes.
   * @param report a ReportData
   * @param onComplete a callback function
   */
  _buildPathEventsForReport : function (bugStore, report, onComplete) {
    var that = this;

    bugStore.push({
      name       : "Line " + report.lastBugPosition.startLine + " : " +
        report.checkerId,
      id         : report.bugHash,
      parent     : CC_UTIL.severityFromCodeToString(report.severity),
      range      : report.lastBugPosition,
      reportId   : report.reportId,
      checkerId  : report.checkerId,
      suppressed : report.suppressed,
      isLeaf     : false
    });

    bugStore.push({
      name       : "<b><u>Result</u> : " + report.checkerMsg + "</b>",
      id         : report.bugHash + "_0",
      parent     : report.bugHash,
      range      : report.lastBugPosition,
      filePath   : that.filePath,
      fileId     : report.fileId,
      reportId   : report.reportId,
      checkerId  : report.checkerId,
      suppressed : report.suppressed,
      isLeaf     : true
    });

    CC_SERVICE.getReportDetails(report.reportId, function (details) {
      if (details instanceof RequestFailed) {
        console.error("Failed to load report details!", details);
        onComplete();
        return;
      }

      details.pathEvents.forEach(function (step, index) {
        bugStore.push({
          name       : "Line " + step.startLine + " : " + step.msg,
          id         : report.bugHash + "_" + (index + 1),
          parent     : report.bugHash,
          range      : step,
          filePath   : step.filePath,
          fileId     : step.fileId,
          reportId   : report.reportId,
          checkerId  : report.checkerId,
          suppressed : report.suppressed,
          isLeaf     : true
        });
      });

      onComplete();
    });
  },


  /**
   * Start (async) loading the bug tree.
   */
  loadBugStoreData : function () {
    var that = this;

    var bugStoreDataTmp = [
      {
        name : "Bugs by priority",
        id   : "root"
      },{
        name   : "Critical",
        id     : "critical",
        parent : "root",
        isLeaf : false
      },{
        name   : "High",
        id     : "high",
        parent : "root",
        isLeaf : false
      },{
        name   : "Medium",
        id     : "medium",
        parent : "root",
        isLeaf : false
      },{
        name   : "Low",
        id     : "low",
        parent : "root",
        isLeaf : false
      },{
        name   : "Style",
        id     : "style",
        parent : "root",
        isLeaf : false
      },{
        name   : "Unspecified",
        id     : "unspecified",
        parent : "root",
        isLeaf : false
      }
    ];

    that._queryReportsForFile(function (reports) {
      var reportsComplete = 0;

      reports.forEach(function (report) {
        that._buildPathEventsForReport(bugStoreDataTmp, report, function () {
          ++reportsComplete;
          if (reportsComplete === reports.length) {
            // FIXME: it's slow on large array
            bugStoreDataTmp.forEach(function (item) {
              that.bugStore.put(item, { overwrite : true });
            });

            if (that.onLoaded) {
              that.onLoaded();
            }
          }
        });
      });
    });
  }



});});
