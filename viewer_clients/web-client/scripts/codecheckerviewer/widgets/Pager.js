// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/dom-construct",
  "dojo/dom-attr",
  "dijit/_WidgetBase",
  "dijit/form/Button",
  "dijit/form/Select"
], function(declare, domConstruct, domAttr, _WidgetBase, Button, Select) {
return declare(_WidgetBase, {


  constructor : function(args) {
    declare.safeMixin(this, args);

    this.pageNumber = 1;
  },


  buildRendering : function() {
    this.domNode = domConstruct.create("div", {
      class : "pagerWidget"
    });
  },


  postCreate : function() {
    this.inherited(arguments);

    this.resultCount = domConstruct.create("span", {
      innerHTML : "Results per page:",
      style     : "font-size: 11pt; margin-right: 5px;"
    });

    this.resultCountPerPageSelect = new Select({
      forceWidth : true,
      options    : [
        { label: "5", value: 5 },
        { label: "10", value: 10 },
        { label: "50", value: 50, selected: true },
        { label: "100", value: 100 },
        { label: "500", value: 500 }
      ],
      style    : "width: 50px; margin-right: 40px; font-size: 11pt;",
      onChange : (function(_this) {
        return function(val) {
          _this.refreshPager();
        };
      })(this)
    });

    this.arrowLeftButton = new Button({
      iconClass : "arrowLeftIcon",
      showLabel : false,
      style     : "border: 0px; margin: 0px; padding: 0px;",
      onClick   : (function(_this) {
        return function() {
          _this.arrowPress("left");
        };
      })(this)
    });

    this.arrowRightButton = new Button({
      iconClass : "arrowRightIcon",
      showLabel : false,
      style     : "border: 0px; margin: 0px; padding: 0px;",
      onClick   : (function(_this) {
        return function() {
          _this.arrowPress("right");
        };
      })(this)
    });

    this.actualPageLabel = domConstruct.create("span", {
      innerHTML : "1",
      style     : "font-size: 11pt; margin-left: 10px; margin-right: 10px;"
    });

    domConstruct.place(this.resultCount, this.domNode);
    domConstruct.place(this.resultCountPerPageSelect.domNode, this.domNode);
    domConstruct.place(this.arrowLeftButton.domNode, this.domNode);
    domConstruct.place(this.actualPageLabel, this.domNode);
    domConstruct.place(this.arrowRightButton.domNode, this.domNode);
  },


  arrowPress : function(direction) {
    if (direction === "left") {
      this.pageNumber -= 1;
    } else if (direction === "right") {
      this.pageNumber += 1;
    }

    this.myOverviewTC.overviewGrid.refreshGrid();

    this.disableArrowsAsNeeded();

    this.updateActualPageLabel();
  },


  refreshPager : function() {
    this.pageNumber = 1;

    this.updateActualPageLabel();

    this.myOverviewTC.overviewGrid.refreshGrid();

    this.disableArrowsAsNeeded();
  },


  disableArrowsAsNeeded : function() {
    if (this.pageNumber === 1) {
      this.arrowLeftButton.setDisabled(true);
    } else {
      this.arrowLeftButton.setDisabled(false);
    }
    if (this.pagingToRightAllowed === false) {
      this.arrowRightButton.setDisabled(true);
    } else {
      this.arrowRightButton.setDisabled(false);
    }
  },


  updateActualPageLabel : function() {
    domAttr.set(this.actualPageLabel, "innerHTML", "" + this.pageNumber);
  },


  setPagingToRightAllowed : function(resultCount) {
    if (resultCount > 0) {
      this.pagingToRightAllowed = true;
    } else {
      this.pagingToRightAllowed = false;
    }
  },


  getPagerParams: function() {
    var resultsPerPage = this.resultCountPerPageSelect.getValue();

    return { resultsPerPage: resultsPerPage, pageNumber: this.pageNumber };
  },


  getCurrentPageNumber: function() {
    return this.pageNumber;
  }


});});