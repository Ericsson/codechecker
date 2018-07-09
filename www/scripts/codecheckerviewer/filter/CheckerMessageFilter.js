// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter'],
function (declare, Deferred, SelectFilter) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      serverSide : true,
      regex : true,
      placeHolder : 'Search for checker messages...'
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
      });
      return deferred;
    }
  });
});
