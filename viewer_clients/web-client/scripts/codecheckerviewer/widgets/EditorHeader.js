// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/dom-construct",
  "dijit/_WidgetBase",
  "dijit/form/Button",
], function ( declare, domConstruct, _WidgetBase, Button ) {
return declare(_WidgetBase, {


  constructor: function() {
    this.suppressButton = new Button({
      label     : "Suppress bug",
      showLabel : true,
      style     : "margin : 0px; margin-right : 5px;"
    });

    this.documentationButton = new Button({
      label     : "Show documentation",
      showLabel : true,
      style     : "margin : 0px;"
    });
  },


  buildRendering : function() {
    this.domNode = domConstruct.create("div", {
      class: "editorHeader"
    });
  },


  postCreate : function() {
    this.inherited(arguments);

    domConstruct.place(this.suppressButton.domNode, this.domNode);
    domConstruct.place(this.documentationButton.domNode, this.domNode);
  }


});});
