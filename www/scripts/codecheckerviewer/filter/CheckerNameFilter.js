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
      placeHolder : 'Search for checker names...'
    },

    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.checkerName = opt.query ? opt.query : null;

      var deferred = new Deferred();
      CC_SERVICE.getCheckerCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, opt.limit, opt.offset, function (res) {
        deferred.resolve(res.map(function (checker) {
          return {
            value : checker.name,
            count : checker.count
          };
        }));
      });
      return deferred;
    }
  });
});
