// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dojo/Deferred',
  'dijit/Dialog',
  'codechecker/filter/SelectFilter',
  'codechecker/SourceComponentManager',
  'codechecker/util'],
function (dom, declare, Deferred, Dialog, SelectFilter,
  SourceComponentManager, util) {

  return declare(SelectFilter, {
    search : {
      enable : true,
      placeHolder : 'Search for source components...'
    },

    postCreate : function () {
      this.inherited(arguments);
      var that = this;

      // Source components can be managed only by administrators.
      if (IS_ADMIN_OF_ANY_PRODUCT) {
        this._edit = dom.create('i', {
          class : 'customIcon edit',
          onclick : function () {
            that._manageDialog.show();
          }
        }, this._clean, 'before');

        // Source component manager.
        this._manageDialog = new Dialog({
          title : 'Manage source components',
          style : 'width: 50%;',
          onShow : function () {
            that._sourceComponentManager.showListOfComponentPage();
          }
        });

        this._sourceComponentManager = new SourceComponentManager({
          class : 'source-component-manager',
          style : 'height: 450px;',
          sourceComponentFilter : this
        });
        this._manageDialog.addChild(this._sourceComponentManager);
      }
    },

    formatDescription : function (value) {
      var list = dom.create('ul', { class : 'component-description'});
      value.split('\n').forEach(function (item) {
        dom.create('li', {
          innerHTML : item,
          class : 'component-item'
        }, list);
      });
      return list.outerHTML;
    },

    getItems : function () {
      var that = this;

      var deferred = new Deferred();
      CC_SERVICE.getSourceComponents(null, function (res) {
        deferred.resolve(res.map(function (component) {
          return {
            value : component.name,
            description : that.formatDescription(component.value)
          };
        }));
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      return deferred;
    }
  });
});
