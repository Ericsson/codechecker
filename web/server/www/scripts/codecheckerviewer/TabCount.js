// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dijit/_WidgetBase',
  'dojo/_base/declare',
  'dojo/dom-construct'],
function (_WidgetBase, declare, dom) {
  return declare(_WidgetBase, {
    postCreate : function () {
      this._tabCountWrapper = dom.create('span', {
        class : 'tab-count-wrapper',
        innerHTML : this.get('title')
      });

      this._tabCount = dom.create('span', {
        class : 'tab-count',
        innerHTML : '?'
      }, this._tabCountWrapper);

      this._updateTitle();
    },

    _setTabCountAttr : function (value) {
      this._tabCount.innerHTML = value;
      this._updateTitle();
    },

    _updateTitle : function () {
      this.set('title', this._tabCountWrapper.innerHTML);
    }
  });
});
