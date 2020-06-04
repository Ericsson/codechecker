// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dojo/dom-class',
  'dijit/form/TextBox',
  'codechecker/filter/SelectFilter'],
function (dom, declare, domClass, TextBox, SelectFilter) {
  return declare(SelectFilter, {

    minCharacters : 5,

    constructor : function () {
      this.minCharacterMsg = 'At least ' + this.minCharacters
                           + ' characters must be given!';
    },

    postCreate : function () {
      var that = this;

      // Initialize the header of the filter.
      this.initHeader(false, true);

      this._notEnoughChar = dom.create('i', {
        class : 'customIcon warn hide',
        title : this.minCharacterMsg
      }, this._title, 'after');

      this._reportHashFilter = new TextBox({
        class : 'report-hash-filter-input',
        placeHolder : 'Search for report hash (min 5 characters)...',
        onKeyUp : function () {
          clearTimeout(this.timer);

          var value = this.get('value');

          // Show warning message if necessary.
          if (!value || value.length >= that.minCharacters) {
            that.hideNotEnoughCharMsg();
          } else {
            that.showNotEnoughCharMsg();
            return;
          }

          this.timer = setTimeout(function () {
            that.filterChanged();
          }, 500);
        }
      });
      dom.place(this._reportHashFilter.domNode, this.domNode);
    },

    getValue : function () {
      return this._reportHashFilter.get('value');
    },

    setValue : function (value) {
      this._reportHashFilter.set('value', value);
    },

    // Being called when report hash filter is changed.
    filterChanged : function () {
      var that = this;

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
      this.notifyOthers();

      // Set the focus back to the input field.
      setTimeout(function () { that._reportHashFilter.focus(); }, 0);
    },

    getUrlState : function () {
      var state = {};

      var value = this.getValue();
      state[this.class] = value && value.length ? value : null;

      return state;
    },

    initByUrl : function (queryParams) {
      var state = queryParams[this.class] ? queryParams[this.class] : null;
      this.setValue(state);
      this.updateReportFilter(state);
    },

    getSelectedItemValues : function () {
      return this.getValue();
    },

    clear : function () {
      this.updateReportFilter(null);
      this.setValue(null);
    },

    showNotEnoughCharMsg: function () {
      domClass.remove(this._notEnoughChar, 'hide');
    },

    hideNotEnoughCharMsg : function () {
      domClass.add(this._notEnoughChar, 'hide');
    },

    notify : function () {}
  });
});
