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
      regexLabel : 'Filter by wildcard pattern (e.g.: core*): ',
      placeHolder : 'Search for checker names (e.g.: core*)...'
    },

    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.checkerName = opt.query ? opt.query : null;

      var deferred = new Deferred();
      CC_SERVICE.getCheckerCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, null, 0, function (res) {
        deferred.resolve(res.map(function (checker) {
          return {
            value : checker.name,
            count : checker.count
          };
        }));
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      return deferred;
    }
  });
});
