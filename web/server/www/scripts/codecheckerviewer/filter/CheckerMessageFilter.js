// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter',
  'codechecker/util'],
function (declare, Deferred, SelectFilter, util) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      serverSide : true,
      regex : true,
      regexLabel : 'Filter by wildcard pattern (e.g.: *deref*): ',
      placeHolder : 'Search for checker messages (e.g.: *deref*)...'
    },

    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.checkerMsg = opt.query ? opt.query : null;

      if (opt.selected)
        opt.reportFilter.checkerMsg = opt.selected;

      var deferred = new Deferred();
      CC_SERVICE.getCheckerMsgCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, opt.limit, opt.offset, function (res) {
        deferred.resolve(Object.keys(res).map(function (msg) {
          return {
            value : msg,
            count : res[msg]
          };
        }));
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      return deferred;
    }
  });
});
