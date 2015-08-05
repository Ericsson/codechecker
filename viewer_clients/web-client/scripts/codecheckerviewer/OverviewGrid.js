// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/data/ItemFileWriteStore",
  "dojox/grid/DataGrid",
], function ( declare, ItemFileWriteStore, DataGrid ) {
return declare(DataGrid, {

  // myOverviewTC


  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);


    that.store = new ItemFileWriteStore({
      data: { identifier: "id", items: [] }
    });

    that.cellWidth = ((100)/5).toString() + "%";

    that.structure = [
      { name: "Index", field: "id", styles: "text-align: center;", width: "40px" },
      { name: "File", field: "fileWithBugPos", styles: "text-align: center;", width: that.cellWidth , formatter: function(data) { return data.split('\n').join('<br/>'); } },
      { name: "Message", field: "checkerMsg", styles: "text-align: center;", width: that.cellWidth },
      { name: "Checker name", field: "checkerId", styles: "text-align: center;", width: that.cellWidth },
      { name: "Severity", field: "severity", styles: "text-align: center;", width: that.cellWidth },
      { name: "Suppress Comment", field: "suppressComment", styles: "text-align: center;", width: that.cellWidth },
    ];

    marked.setOptions({ highlight: function (code) { return hljs.highlightAuto(code).value; } });

  },



  fillOverviewGrid : function(filterObjArray, pagerObj) {
    // filterObjArray = [ { supprState, severityState, pathState, checkerTypeState, (resolvState) } ]
    // pagerObj = { resultsPerPage, pageNumber}

    var that = this;


    var sortBySeverityDESC = new codeCheckerDBAccess.SortMode();
    sortBySeverityDESC.type = codeCheckerDBAccess.SortType["SEVERITY"];
    sortBySeverityDESC.ord  = codeCheckerDBAccess.Order["DESC"];

    var sortByCheckerNameASC = new codeCheckerDBAccess.SortMode();
    sortByCheckerNameASC.type = codeCheckerDBAccess.SortType["CHECKER_NAME"];
    sortByCheckerNameASC.ord  = codeCheckerDBAccess.Order["ASC"];

    var sortByFileNameASC = new codeCheckerDBAccess.SortMode();
    sortByFileNameASC.type = codeCheckerDBAccess.SortType["FILENAME"];
    sortByFileNameASC.ord  = codeCheckerDBAccess.Order["ASC"];

    var sorts = [sortBySeverityDESC, sortByFileNameASC, sortByCheckerNameASC];


    var reportDataList = [];
    var runIdToAdd = null;


    if (that.myOverviewTC.overviewType === "run") {

      var pagerStatus = that.myOverviewTC.overviewPager.getPagerParams();
      var idNumber = 1 + pagerStatus.resultsPerPage * (pagerStatus.pageNumber - 1);

      var filters = [];

      for (var i = 0 ; i < filterObjArray.length ; ++i) {
        var filter = new codeCheckerDBAccess.ReportFilter();

        filter.checkerId = filterObjArray[i].checkerTypeState;

        var filepathTmp = filterObjArray[i].pathState;
        filter.filepath = filepathTmp === "" ? "*" : filepathTmp;

        var severityTmp = filterObjArray[i].severityState;

        if (severityTmp !== "all") {
           filter.severity = parseInt(severityTmp);
        }

        switch (filterObjArray[i].supprState) {
          case "supp":
            filter.suppressed = true;
            break;
          case "unsupp":
            filter.suppressed = false;
            break;
          case "all":
            // DO NOTHING
            break;
        }

        filters.push(filter);
      }

      runIdToAdd = that.myOverviewTC.runId;

      reportDataList = CC_SERVICE.getRunResults(
        runIdToAdd,
        pagerObj.resultsPerPage,
        pagerObj.resultsPerPage * (pagerObj.pageNumber - 1),
        sorts,
        filters
      );
      that.insertIntoStore(that.store, reportDataList, runIdToAdd, idNumber);


      var resultsLeft = CC_SERVICE.getRunResults(
        runIdToAdd,
        1,
        pagerObj.resultsPerPage * pagerObj.pageNumber,
        [],
        filters
      );
      that.myOverviewTC.overviewPager.setPagingToRightAllowed(resultsLeft.length);

    } else if (that.myOverviewTC.overviewType === "diff") {

      var idNumber = 1;

      var newResultsFilters = [];
      var resolvedResultsFilters = [];
      var unresolvedResultsFilters = [];

      for (var i = 0 ; i < filterObjArray.length ; ++i) {
        var filter = new codeCheckerDBAccess.ReportFilter();

        filter.checkerId = filterObjArray[i].checkerTypeState;

        var filepathTmp = filterObjArray[i].pathState;
        filter.filepath = filepathTmp === "" ? "*" : filepathTmp;

        var severityTmp = filterObjArray[i].severityState;

        if (severityTmp !== "all") {
           filter.severity = parseInt(severityTmp);
        }

        switch (filterObjArray[i].supprState) {
          case "supp":
            filter.suppressed = true;
            break;
          case "unsupp":
            filter.suppressed = false;
            break;
          case "all":
            // DO NOTHING
            break;
        }

        switch (filterObjArray[i].resolvState) {
          case "newonly":
            newResultsFilters.push(filter);
            break;
          case "resolv":
            resolvedResultsFilters.push(filter);
            break;
          case "unresolv":
            unresolvedResultsFilters.push(filter);
            break;
        }
      }


      // newResults
      if (newResultsFilters.length > 0) {
        runIdToAdd = that.myOverviewTC.runId2;
        reportDataList = CC_SERVICE.getNewResults(
          that.myOverviewTC.runId1,
          that.myOverviewTC.runId2,
          codeCheckerDBAccess.MAX_QUERY_SIZE,
          0,
          sorts,
          newResultsFilters
        );
        that.insertIntoStore(that.store, reportDataList, runIdToAdd, idNumber);
      }


      // resolved
      if (resolvedResultsFilters.length > 0) {
        idNumber += reportDataList.length;
        runIdToAdd = that.myOverviewTC.runId1;
        reportDataList = CC_SERVICE.getResolvedResults(
          that.myOverviewTC.runId1,
          that.myOverviewTC.runId2,
          codeCheckerDBAccess.MAX_QUERY_SIZE,
          0,
          sorts,
          resolvedResultsFilters
        );
        that.insertIntoStore(that.store, reportDataList, runIdToAdd, idNumber);
      }


      // unresolved
      if (unresolvedResultsFilters.length > 0) {
        idNumber += reportDataList.length;
        runIdToAdd = that.myOverviewTC.runId2;
        reportDataList = CC_SERVICE.getUnresolvedResults(
          that.myOverviewTC.runId1,
          that.myOverviewTC.runId2,
          codeCheckerDBAccess.MAX_QUERY_SIZE,
          0,
          sorts,
          unresolvedResultsFilters
        );
        that.insertIntoStore(that.store, reportDataList, runIdToAdd, idNumber);
      }

      // Code for Pager to work consistently would be here. Right now it is not
      // feasible to use Pager with Diff Overview.

    }
  },



  refreshGrid : function() {
    this.recreateStore();

    if (this.myOverviewTC.overviewType === "run") {

      this.fillOverviewGrid(
        this.myOverviewTC.getStateOfFilters(),
        this.myOverviewTC.overviewPager.getPagerParams()
      );


    } else if (this.myOverviewTC.overviewType === "diff") {

      this.fillOverviewGrid(
        this.myOverviewTC.getStateOfFilters()
      );

    }

    this.render();
  },



  insertIntoStore : function(store, reportDataList, runIdToAdd, firstNewId) {
    var that = this;


    for (var i = 0 ; i < reportDataList.length ; ++i) {
      store.newItem({
        id             : firstNewId + i,
        checkerId      : reportDataList[i].checkerId,
        bugHash        : reportDataList[i].bugHash,
        checkedFile    : reportDataList[i].checkedFile,
        checkerMsg     : reportDataList[i].checkerMsg,
        reportId       : reportDataList[i].reportId,
        suppressed     : reportDataList[i].suppressed,
        fileId         : reportDataList[i].fileId,
        lastBugPosition: reportDataList[i].lastBugPosition,
        severity       : CC_UTIL.severityFromCodeToString(reportDataList[i].severity),
        suppressComment: reportDataList[i].suppressComment === null ? "----" : reportDataList[i].suppressComment,
        fileWithBugPos : reportDataList[i].checkedFile + "\n@ Line " + reportDataList[i].lastBugPosition.startLine,
        runId          : runIdToAdd
      });
    }
  },



  recreateStore: function() {
    newStore = new ItemFileWriteStore({
      data: {
        identifier: "id", items: []
      }
    });

    this.setStore(newStore);
  }


});});
