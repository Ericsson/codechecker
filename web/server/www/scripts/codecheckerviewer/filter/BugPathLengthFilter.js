// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'dojo/dom-construct',
  'dijit/form/NumberTextBox',
  'codechecker/filter/SelectFilter'],
function (declare, Deferred, dom, NumberTextBox, SelectFilter) {

  return declare(SelectFilter, {
    postCreate : function () {
      var that = this;

      // Initialize the header of the filter.
      this.initHeader(false, true);

      var bugPathLenWrapper =
        dom.create('div', { class : 'bug-path-length-wrapper' }, this.domNode);

      //--- Bug path length filter input boxes. ---//

      this._minBugPathLength = new NumberTextBox({
        class       : 'min-bug-path-length',
        placeholder : 'min...',
        onKeyUp     : function () {
          clearTimeout(this.timer);

          this.timer = setTimeout(function () {
            that.filterChanged();
          }, 500);
        }
      });
      dom.place(this._minBugPathLength.domNode, bugPathLenWrapper);

      this._maxBugPathLength = new NumberTextBox({
        class       : 'max-bug-path-length',
        placeholder : 'max...',
        onKeyUp     : function () {
          clearTimeout(this.timer);

          this.timer = setTimeout(function () {
            that.filterChanged();
          }, 500);
        }
      });
      dom.place(this._maxBugPathLength.domNode, bugPathLenWrapper);
    },

    // Being called when bug path length filter is changed.
    filterChanged : function () {
      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
      this.notifyOthers();
    },

    getItems : function () {
      var deferred = new Deferred();
      deferred.resolve([]);
      return deferred;
    },

    getUrlState : function () {
      var state = {};

      var minBugPathLength = this._minBugPathLength.get('value');
      state[this._minBugPathLength.class] =
        isNaN(minBugPathLength) ? null : minBugPathLength;

      var maxBugPathLength = this._maxBugPathLength.get('value');
      state[this._maxBugPathLength.class] =
        isNaN(maxBugPathLength) ? null : maxBugPathLength;

      return state;
    },

    initByUrl : function (queryParams) {
      var minBugPathLength = queryParams[this._minBugPathLength.class];
      if (!isNaN(minBugPathLength)) {
        this._minBugPathLength.set('value', minBugPathLength, false);
      }

      var maxBugPathLength = queryParams[this._maxBugPathLength.class];
      if (!isNaN(maxBugPathLength)) {
        this._maxBugPathLength.set('value', maxBugPathLength, false);
      }

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    getSelectedItemValues : function () {
      var state = this.getUrlState();
      return {
        minBugPathLength : state[this._minBugPathLength.class],
        maxBugPathLength : state[this._maxBugPathLength.class],
      };
    },

    clear : function () {
      this._minBugPathLength.set('value', null, false);
      this._maxBugPathLength.set('value', null, false);

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    notify : function () {
    }
  });
});
