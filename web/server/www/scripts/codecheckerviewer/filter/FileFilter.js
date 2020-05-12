// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter',
  'codechecker/util'],
function (dom, declare, Deferred, SelectFilter, util) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      serverSide : true,
      regex : true,
      regexLabel : 'Filter by wildcard pattern (e.g.: */src/*): ',
      placeHolder : 'Search for files (e.g.: */src/*)...'
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
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      return deferred;
    }
  });
});
