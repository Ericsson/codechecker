// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/dom-construct",
  "dijit/DropDownMenu",
  "dijit/MenuItem",
  "dijit/form/DropDownButton",
  "dijit/layout/ContentPane",
  "dijit/Dialog",
], function(declare, domConstruct, DropDownMenu, MenuItem, DropDownButton
           , ContentPane, Dialog) {
return declare(DropDownButton, {

  // mainTC


  constructor : function(args) {
    declare.safeMixin(this, args);

    this.iconClass = "dijitIconFunction";
  },


  postCreate : function() {
    this.inherited(arguments);

    this.mainDropDownMenu = new DropDownMenu({
      style : "display: none;"
    });

    this.menuItemDocumentation = new MenuItem({
      label   : "Documentation",
      onClick : (function(_this) {
        return function() {

          var documentationCP;

          documentationCP = new ContentPane({
            title    : "Documentation",
            closable : true,
            style    : "margin: 0px; padding: 0px; border: 0px;",
            content  : domConstruct.create("iframe", {
              src   : "/docs/index.html",
              style : "height: 98%; width: 100%; margin: 0px; border: 0px; padding: 0px; padding-top: 4px;"
            })
          });

          _this.mainTC.addChild(documentationCP);
          _this.mainTC.selectChild(documentationCP);

        };
      })(this)
    });

    this.menuItemCredits = new MenuItem({
      label   : "Credits",
      onClick : function() {
        var catDialog;

        catDialog = new Dialog({
          style   : "width: 300px; height: 400px; text-align: center;"
        });

        catDialog.show();
      }
    });

    this.mainDropDownMenu.addChild(this.menuItemDocumentation);
    this.mainDropDownMenu.addChild(this.menuItemCredits);

    this.dropDown = this.mainDropDownMenu;
  }


});});
