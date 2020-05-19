// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dijit/form/TextBox',
  'dijit/layout/ContentPane'],
function (declare, domConstruct,
  TextBox, ContentPane, util) {

  return declare(ContentPane, {
    constructor : function () {
      var that = this;

      this._txtAlert = new TextBox({
        name        : 'notif-alert-input',
        id          : 'notif-alert-input',
        class       : 'form-input',
        placeholder : 'Write your alert here!'
      });
    },

    postCreate : function () {
      this.inherited(arguments);

      //--- Set up the form ---//

      var notifContainer = domConstruct.create('div', {
        class : 'formElement'
      }, this.containerNode);

      var alertLabel = domConstruct.create('notif-label', {
        class     : 'formLabel bold',
        innerHTML : 'Notification: '
      });
      domConstruct.place(alertLabel, notifContainer);

      domConstruct.place(this._txtAlert.domNode, notifContainer);
    }
  });
});
