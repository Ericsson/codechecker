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


  constructor : function() {
    var that = this;

    that.store = new ItemFileWriteStore({
      data: { identifier: "id", items: [] }
    });

    that.structure = [
      { name: "Diff", field: "diffDisplay", styles: "text-align: center;", width: "25px", type: "dojox.grid.cells.Bool", editable: true },
      { name: "Run Id", field: "runid", styles: "text-align: center;", width: "50px" },
      { name: "Name", field: "name", styles: "text-align: center;", width: "auto" },
      { name: "Date", field: "date", styles: "text-align: center;", width: "auto" },
      { name: "Number of bugs", field: "numberofbugs", styles: "text-align: center;", width: "auto" },
      { name: "Duration", field: "duration", styles: "text-align: center;", width: "auto" },
      { name: "Delete", field: "deleteDisplay", styles: "text-align: center;", width: "50px", type: "dojox.grid.cells.Bool", editable: true },
    ];

  },


  /**
   * Fills the ListOfRunsGrid with RunData
   */
  fillGridWithRunData : function() {
    var that = this;

    CC_SERVICE.getRunData(function(runDataList) {
      runDataList.forEach(function(item) {
        var currItemDate = "Failed run";

        if (-1 !== item.runDate) {
          currItemDate = item.runDate.split(/[\s\.]+/);
        }

        that.store.newItem({
          id           : item.runId,
          runid        : item.runId,
          name         : item.name,
          date         : currItemDate[0] + " --- " + currItemDate[1],
          numberofbugs : item.resultCount,
          duration     : item.duration + " sec",
          diffDisplay  : false,
          diffActual   : false,
          deleteDisplay: false,
          deleteActual : false
        });
      });
    });
  },

  /**
   * Gets the number of the ticked checkboxes of the Diff column in the
   * ListOfRunsGrid (This should be 0 or 1 or 2)
   */
  getDiffNumber : function() {
    var that = this;

    var accm = 0;

    for (var i = 0 ; i < that.store._arrayOfAllItems.length ; ++i) {
      if (that.getItem(i).diffActual[0] === true) { ++accm; }
    }

    return accm;
  },


  /**
   * Completely recreates the store to an empty state.
   */
  recreateStore : function() {
    var that = this;

    var newStore = new ItemFileWriteStore({
      data: {
        identifier: "id",
        items: []
      }
    });

    that.setStore(newStore);
  }


});});
