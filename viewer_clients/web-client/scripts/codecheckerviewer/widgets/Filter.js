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

    if (that.myOverviewTC.overviewType === "run") {
      that.initRun();
    } else if (that.myOverviewTC.overviewType === "diff") {
      that.initDiff();
    }
  },


  /**
   * Initializes the widgets that both Runs and Diffs share.
   */
  initShared : function () {
    var that = this;

    that.textBoxPath = new TextBox({
      placeHolder : "Path filter",
      style       : "width: 200px; margin-right: 5px;",
      onKeyPress  : function(evt) {
        if (evt.keyCode === 13) { // "Enter"
          that.pathAndSelectOnChange(true);
        }
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
        that.pathAndSelectOnChange(true);
      }
    });
  },


  /**
   * Initializes the shared and Run-specific widgets for a Run.
   */
  initRun : function () {
    var that = this;

    that.initShared();

    that.selectCheckerInfo = new Select({
      forceWidth : true,
      options    : that.filterOptions.checkerInfoOptions,
      style      : "margin-right: 5px;",
      onChange   : function(val) {
        that.pathAndSelectOnChange(false);
      }
    });

    domConstruct.place(that.textBoxPath.domNode, that.domNode);
    domConstruct.place(that.selectSuppr.domNode, that.domNode);
    domConstruct.place(that.selectCheckerInfo.domNode, that.domNode);
  },


  /**
   * Initializes the shared and Diff-specific widgets for a Diff.
   */
  initDiff : function () {
    var that = this;

    that.initShared();

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


    domConstruct.place(that.textBoxPath.domNode, that.domNode);
    domConstruct.place(that.selectSeverity.domNode, that.domNode);
    domConstruct.place(that.selectSuppr.domNode, that.domNode);
    domConstruct.place(that.selectCheckerType.domNode, that.domNode);
    domConstruct.place(that.selectResolv.domNode, that.domNode);
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


  /**
   * Refreshes the Grid according to the current filters.
   * If called in a Run Overview, and called by NOT a checkerInfo Select, then
   * refreshes the checkerInfo Select of the particular filter. In this case,
   * the function is asyncronous.
   */
  pathAndSelectOnChange : function(refreshCheckerOptions) {
    var that = this;

    if (that.myOverviewTC.overviewType === "run" && refreshCheckerOptions === true) {
      var filePath = "*" + that.textBoxPath.get("value") + "*";
      var suppressed = that.selectSuppr.get("value") === "supp" ? true : false;

      CC_UTIL.getCheckerInfoRun(
        that.myOverviewTC.runId,
        filePath,
        suppressed,
        function (checkerInfo) {
          var newCheckerInfoOptions = CC_UTIL.normalizeCheckerInfo(checkerInfo);

          that.filterOptions.checkerInfoOptions = newCheckerInfoOptions;
          that.selectCheckerInfo.set("options", newCheckerInfoOptions);

          that.selectCheckerInfo.reset();

          that.myOverviewTC.overviewGrid.refreshGrid();
        }
      );
    } else {
      that.myOverviewTC.overviewGrid.refreshGrid();
    }
  }


});});
