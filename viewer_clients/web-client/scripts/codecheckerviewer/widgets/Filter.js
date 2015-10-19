// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/dom-construct",
  "dijit/_WidgetBase",
  "dijit/form/TextBox",
  "dijit/form/Button",
  "dijit/form/Select",
], function ( declare, domConstruct, _WidgetBase, TextBox, Button, Select ) {
return declare(_WidgetBase, {


  /**
   * Construct the new object. The following arguments are required:
   *   myOverviewTC: The OverviewTC this object belongs to.
   *   filterOptions: object of Select-compatible options array to be used by
   *     Selects in a Filter, contains: checkerTypeOptions, severityOptions.
   */
  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);
  },


  buildRendering : function() {
    var that = this;

    that.domNode = domConstruct.create("div", {
      style: "border: 0px; margin: 5px;"
    });
  },

  /**
   * Builds the widget dom.
   */
  postCreate : function() {
    var that = this;
    that.inherited(arguments);

    that.textBoxPath = new TextBox({
      placeHolder : "Path filter, i.e. *filename.*",
      style       : "width: 200px; margin-right: 5px;",
      onKeyPress  : function(evt) {
        if (evt.keyCode === 13) { // "Enter"
          that.pathAndSelectOnChange();
        }
      }
    });

    if (that.filterOptions === undefined) {
      that.filterOptions = {};
      that.filterOptions.severityOptions =
        CC_UTIL.getAvailableSeverityLevels();
      that.filterOptions.checkerTypeOptions =
        CC_UTIL.getAvailableCheckers(that.myOverviewTC);
    }

    that.selectSeverity = new Select({
      forceWidth : true,
      options    : that.filterOptions.severityOptions,
      style      : "margin-right: 5px;",
      onChange   : function(val) {
        that.pathAndSelectOnChange();
      }
    });

    that.selectCheckerType = new Select({
      forceWidth : true,
      options    : that.filterOptions.checkerTypeOptions,
      style      : "margin-right: 5px;",
      onChange   : function(val) {
        that.pathAndSelectOnChange();
      }
    });

    that.selectSuppr = new Select({
      forceWidth : true,
      options    : [
        { label : "Unsuppressed", value : "unsupp", selected: true },
        { label : "Suppressed"  , value : "supp"                   }
      ],
      style      : "margin-right: 5px;",
      onChange   : function(val) {
        that.pathAndSelectOnChange();
      }
    }, domConstruct.create("div"));


    // Add Resolved select if it is an overview of a Diff
    if (that.myOverviewTC.overviewType === "diff") {

      that.selectResolv = new Select({
        forceWidth : true,
        options    : [
          { label : "New only"  , value : "newonly" },
          { label : "Resolved"  , value : "resolv" },
          { label : "Unresolved", value : "unresolv", selected: true }
        ],
        style      : "margin-right: 5px;",
        onChange   : function(val) {
          that.pathAndSelectOnChange();
        }
      });

    }


    domConstruct.place(that.textBoxPath.domNode, that.domNode);
    domConstruct.place(that.selectSeverity.domNode, that.domNode);
    domConstruct.place(that.selectSuppr.domNode, that.domNode);
    domConstruct.place(that.selectCheckerType.domNode, that.domNode);

    if (that.myOverviewTC.overviewType === "diff") {
      domConstruct.place(that.selectResolv.domNode, that.domNode);
    }
  },


  addPlusButton : function() {
    var that = this;

    that.plusButton = new Button({
      iconClass : "plusIcon",
      showLabel : false,
      onClick   : function() {
        that.myOverviewTC.overviewHeader.addFilter();
      }
    });

    domConstruct.place(that.plusButton.domNode, that.domNode);
  },


  addMinusButton : function() {
    var that = this;

    that.minusButton = new Button({
      iconClass : "minusIcon",
      showLabel : false,
      onClick   : function() {
        that.myOverviewTC.overviewHeader.removeFilter(that);
      }
    });

    domConstruct.place(that.minusButton.domNode, that.domNode);
  },


  removePlusButton : function() {
    var that = this;

    that.domNode.removeChild(that.plusButton.domNode);
  },


  removeMinusButton : function() {
    var that = this;

    that.domNode.removeChild(that.minusButton.domNode);
  },


  pathAndSelectOnChange : function() {
    var that = this;

    that.myOverviewTC.overviewGrid.refreshGrid();
  }


});});
