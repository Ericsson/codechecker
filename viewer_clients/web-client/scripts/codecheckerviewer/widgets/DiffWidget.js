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
    this.region = "bottom";
  },


  buildRendering : function() {
    this.domNode = domConstruct.create("div", {
      class: "diffWidget"
    });
  },


  postCreate : function() {
    this.inherited(arguments);

    this.diffButton = new Button({
      label    : "Diff",
      style    : "border: 0px; margin: 0px; padding: 0px; margin-right: 20px;",
      disabled : true,
      onClick  : function() {
        CCV.newDiffOverviewTab(CCV.checkedRunIds[0], CCV.checkedRunIds[1],
          CCV.checkedRunNames[0], CCV.checkedRunNames[1]);
      }
    });

    this.baseIdLabel = domConstruct.create("span", {
      style: "font-size: 11pt; margin-right: 20px;"
    });

    this.newIdLabel = domConstruct.create("span", {
      style: "font-size: 11pt; margin-right: 20px;"
    });

    this.setDiffLabel("-", "-");

    domConstruct.place(this.diffButton.domNode, this.domNode);
    domConstruct.place(this.baseIdLabel, this.domNode);
    domConstruct.place(this.newIdLabel, this.domNode);
  },


  setDiffLabel : function(baseID, newID) {
    domAttr.set(this.baseIdLabel, "innerHTML", "Baseline: <b> " + baseID + " </b>");
    domAttr.set(this.newIdLabel, "innerHTML", "NewCheck: <b> " + newID + " </b>");
  },


  setButtonDisabled: function(isDisabled) {
    this.diffButton.set('disabled', isDisabled) ;
  },


  reset: function() {
    this.diffButton.set('disabled', true);
    this.setDiffLabel("-", "-");
  }


});});