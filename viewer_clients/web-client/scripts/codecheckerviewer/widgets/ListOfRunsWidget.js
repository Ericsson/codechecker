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
], function ( declare, domConstruct, domAttr, _WidgetBase, Button ) {
return declare(_WidgetBase, {


  constructor : function() {
    var that = this;
  },


  buildRendering : function() {
    var that = this;

    that.domNode = domConstruct.create("div", {
      class : "listOfRunsWidget"
    });
  },


  postCreate : function() {
    var that = this;
    that.inherited(arguments);

    that.buildDiffPart();
    that.buildDeletePart();

    that.diffAndDeleteTr = domConstruct.create("tr", {
      style : "border: 0px; margin: 0px; padding: 0px;"
    });

    that.widgetTable = domConstruct.create("table", {
      style : "border: 0px; margin: 0px; padding: 0px; width: 100%;"
    });

    domConstruct.place(that.diffButton.domNode, that.diffTd);
    domConstruct.place(that.baseIdLabel, that.diffTd);
    domConstruct.place(that.newIdLabel, that.diffTd);

    domConstruct.place(that.deleteButton.domNode, that.deleteTd);

    domConstruct.place(that.diffTd, that.diffAndDeleteTr);
    domConstruct.place(that.deleteTd, that.diffAndDeleteTr);

    domConstruct.place(that.diffAndDeleteTr, that.widgetTable);

    domConstruct.place(that.widgetTable, that.domNode);
  },


  buildDiffPart : function() {
    var that = this;

    that.diffButton = new Button({
      label    : "Diff",
      style    : "border: 0px; margin: 0px; padding: 0px; margin-right: 20px;",
      disabled : true,
      onClick  : function() {
        CCV.newDiffOverviewTab(CCV.diffRuns[0].runId, CCV.diffRuns[1].runId,
          CCV.diffRuns[0].runName, CCV.diffRuns[1].runName);
      }
    });


    that.baseIdLabel = domConstruct.create("span", {
      style : "font-size: 11pt; margin-right: 20px;"
    });

    that.newIdLabel = domConstruct.create("span", {
      style : "font-size: 11pt; margin-right: 20px;"
    });


    that.diffTd = domConstruct.create("td", {
      style : "border: 0px; margin: 0px; padding: 0px; text-align: left;"
    });

    that.setDiffLabel("-", "-");
  },


  buildDeletePart : function() {
    var that = this;

    that.deleteButton = new Button({
      label    : "Delete",
      style    : "border: 0px; margin: 0px; padding: 0px;",
      disabled : true,
      onClick  : function() {
        CCV.deleteRuns();
      }
    });

    that.deleteTd = domConstruct.create("td", {
      style : "border: 0px; margin: 0px; padding: 0px; text-align: right;"
    });
  },


  setDiffLabel : function(baseID, newID) {
    var that = this;

    domAttr.set(that.baseIdLabel, "innerHTML", "Baseline: <b> " + baseID + " </b>");
    domAttr.set(that.newIdLabel, "innerHTML", "NewCheck: <b> " + newID + " </b>");
  },


  setDiffButtonDisabled: function(isDisabled) {
    var that = this;

    that.diffButton.set('disabled', isDisabled);
  },


  setDeleteButtonDisabled : function(isDisabled) {
    var that = this;

    that.deleteButton.set('disabled', isDisabled);
  },


  reset: function() {
    var that = this;

    that.diffButton.set('disabled', true);
    that.deleteButton.set('disabled', true);
    that.setDiffLabel("-", "-");
  }


});});