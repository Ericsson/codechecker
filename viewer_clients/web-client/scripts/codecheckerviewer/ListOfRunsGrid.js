// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/data/ItemFileWriteStore",
  "dojox/grid/DataGrid",
], function (declare, ItemFileWriteStore, DataGrid) {
return declare(DataGrid, {


  constructor : function () {
    var that = this;

    that.store = new ItemFileWriteStore({
      data: { identifier: "id", items: [] }
    });

    that.structure = [
      { name : "Diff", field : "diffDisplay", styles : "text-align: center;", type : "dojox.grid.cells.Bool", editable : true },
      { name : "Run Id", field : "runid", styles : "text-align: center;" },
      { name : "Name", field : "name", styles : "text-align: left;", width : "100%" },
      { name : "Date", field : "date", styles : "text-align: center;", width : "30%" },
      { name : "Number of bugs", field : "numberofbugs", styles : "text-align: center;", width : "20%" },
      { name : "Duration", field : "duration", styles : "text-align: center;" },
      { name : "Delete", field : "deleteDisplay", styles : "text-align: center;", type : "dojox.grid.cells.Bool", editable : true },
    ];

  },


  /**
   * Fills the ListOfRunsGrid with RunData
   */
  fillGridWithRunData : function () {
    var that = this;

    CC_SERVICE.getRunData(function (runDataList) {

      if (runDataList instanceof RequestFailed) {

        console.log("Thrift API call 'getRunData' failed!");

      } else {

        runDataList.forEach(function (item) {
          if (item.can_delete === undefined || item.can_delete === false) {
            // This item is under removal
            return;
          }

          var prettyDuration = null;
          if (-1 === item.duration) {
            prettyDuration = "--------";
          } else {
            var durHours = Math.floor(item.duration / 3600);
            var durMins  = Math.floor(item.duration / 60) - durHours * 60;
            var durSecs  = item.duration - durMins * 60 - durHours * 3600;

            var prettyDurHours = durHours < 10 ? ("0" + durHours) : durHours;
            var prettyDurMins  = durMins < 10 ? ("0" + durMins) : durMins;
            var prettyDurSecs  = durSecs < 10 ? ("0" + durSecs) : durSecs;

            prettyDuration = prettyDurHours + ":" + prettyDurMins + ":" +
              prettyDurSecs;
          }

          var currItemDate = item.runDate.split(/[\s\.]+/);

          that.store.newItem({
            id            : item.runId,
            runid         : item.runId,
            name          : item.name,
            date          : currItemDate[0] + " --- " + currItemDate[1],
            numberofbugs  : item.resultCount,
            duration      : prettyDuration,
            diffDisplay   : false,
            diffActual    : false,
            deleteDisplay : false,
            deleteActual  : false
          });
        });

      }

    });

  },

  /**
   * Gets the number of the ticked checkboxes of the Diff column in the
   * ListOfRunsGrid (This should be 0 or 1 or 2)
   */
  getDiffNumber : function () {
    var that = this;

    var accm = 0;

    that.store._arrayOfAllItems.forEach(function (e, i) {
      if (that.getItem(i).diffActual[0] === true) {
        ++accm;
      }
    });

    return accm;
  },


  /**
   * Completely recreates the store to an empty state.
   */
  recreateStore : function () {
    var that = this;

    var newStore = new ItemFileWriteStore({
      data : {
        identifier : "id",
        items      : []
      }
    });

    that.setStore(newStore);
  }

});});
