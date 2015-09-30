// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dijit/layout/ContentPane",
  "scripts/codecheckerviewer/widgets/Filter.js",
], function ( declare, ContentPane, Filter ) {
return declare(ContentPane, {


  /**
   * Construct the new object. The following arguments are required:
   *   myOverviewTC: The OverviewTC this object belongs to
   */
  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);

    that.filters = [];
  },


  /**
   * Creates the main Filter widget and builds the dom.
   */
  postCreate : function() {
    var that = this;
    that.inherited(arguments);

    that.mainFilter = new Filter({
      myOverviewTC : that.myOverviewTC
    });

    that.mainFilter.addPlusButton();

    that.filters.push(that.mainFilter);
    that.addChild(that.mainFilter);
  },


  /**
   * Gets the current state of the filters.
   */
  getStateOfFilters : function() {
    var that = this;

    var filterObjArray = [];

    for (var i = 0 ; i < that.filters.length ; ++i) {

      var supprState       = that.filters[i].selectSuppr.get("value");
      var severityState    = that.filters[i].selectSeverity.get("value");
      var pathState        = that.filters[i].textBoxPath.get("value");
      var checkerTypeState = that.filters[i].selectCheckerType.get("value");

      if (that.overviewType === 'run') {
        filterObjArray.push({
          supprState      : supprState,
          severityState   : severityState,
          pathState       : pathState,
          checkerTypeState: checkerTypeState
        });
      } else if (that.overviewType === 'diff') {
        var resolvState = that.filters[i].selectResolv.get("value");
        filterObjArray.push({
          supprState      : supprState,
          resolvState     : resolvState,
          severityState   : severityState,
          pathState       : pathState,
          checkerTypeState: checkerTypeState
        })
      }

    }

    return filterObjArray;
  },


  /**
   * Adds a new filter.
   */
  addFilter : function() {
    var that = this;

    var newFilter = new Filter({
      myOverviewTC : that.myOverviewTC
    });

    newFilter.addMinusButton();

    that.filters.push(newFilter);
    that.addChild(newFilter);

    that.onRemoveOrAdd();
  },


  /**
   * Removes a filter from the filters array and the dom.
   *
   * @param filter The filter to be removed
   */
  removeFilter : function(filter) {
    var that = this;

    for (var i = 0 , len = that.filters.length ; i < len ; ++i ) {
      if (filter === that.filters[i]) {
        that.filters.splice(i, 1);
        that.removeChild(filter);
        that.onRemoveOrAdd();

        break;
      }
    }
  },


  /**
   * Function to be called after adding or removing a filter.
   */
  onRemoveOrAdd : function() {
    var that = this;

    that.myOverviewTC.overviewGrid.refreshGrid();
    that.myOverviewTC.overviewBC.resize();
  }

});});
