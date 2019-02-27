// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'codechecker/filter/FilterBase'],
function (dom, declare, FilterBase) {
  return declare(FilterBase, {
    constructor : function () {
      this._reportCount = 0;
    },

    postCreate : function () {
      var wrapper = dom.create('span', {
        class : 'report-count-wrapper'
      }, this.domNode);

      dom.create('i', { class : 'customIcon bug' }, wrapper);

      this._reportCountWrapper = dom.create('span', {
        class : 'count',
        innerHTML : this._reportCount
      }, wrapper);
    },

    getReportCount : function () {
      return this._reportCount;
    },

    setReportCount : function (count) {
      this._reportCount = count;
      this._reportCountWrapper.innerHTML = count;
    },

    notify : function () {
      var runIds = this.parent.getRunIds();
      var reportFilter = this.parent.getReportFilter();
      var cmpData = this.parent.getCmpData();

      var that = this;
      CC_SERVICE.getRunResultCount(runIds, reportFilter, cmpData,
      function (count) {
        that.setReportCount(count);
      });
    }
  });
});
