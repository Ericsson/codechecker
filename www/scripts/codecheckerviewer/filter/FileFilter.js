// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter'],
function (dom, declare, Deferred, SelectFilter) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      serverSide : true,
      regex : true,
      placeHolder : 'Search for files...'
    },

    labelFormatter : function (label) {
      return '&lrm;' + label + '&lrm;';
    },

    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.filepath = opt.query ? opt.query : null;

      var deferred = new Deferred();
      CC_SERVICE.getFileCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, opt.limit, opt.offset, function (res) {
        // Order the results alphabetically.
        deferred.resolve(Object.keys(res).sort(function (a, b) {
            if (a < b) return -1;
            if (a > b) return 1;
            return 0;
        }).map(function (file) {
          return {
            value : file,
            count : res[file]
          };
        }));
      });
      return deferred;
    }
  });
});
