// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dijit/form/CheckBox',
  'codechecker/filter/FilterBase'],
function (dom, declare, CheckBox, FilterBase) {
  return declare(FilterBase, {
    defaultValue : true,

    postCreate : function () {
      var that = this;
      this._uniqueCheckBox = new CheckBox({
        checked : this.defaultValue,
        onChange : function (isUnique) {
          that.updateReportFilter(isUnique);
          that.parent.notifyAll([that]);
        }
      });
      dom.place(this._uniqueCheckBox.domNode, this.domNode);

      this._uniqueCheckBoxLabel = dom.create('label', {
        for : this._uniqueCheckBox.get('id'),
        innerHTML : 'Unique reports'
      }, this._uniqueCheckBox.domNode, 'after');
    },

    initByUrl : function (queryParams) {
      var state = queryParams[this.class];
      var isUnique = state === 'off' ? false : true;
      this._uniqueCheckBox.set('checked', isUnique, false);
      this.updateReportFilter(isUnique);
    },

    clear : function () {
      this.updateReportFilter(this.defaultValue);
      this._uniqueCheckBox.set('checked', this.defaultValue, false);
    },

    getUrlState : function () {
      var state = {};

      var isUnique = this._uniqueCheckBox.get('checked');
      state[this.class] = isUnique ? null : 'off';

      return state;
    }
  });
});
