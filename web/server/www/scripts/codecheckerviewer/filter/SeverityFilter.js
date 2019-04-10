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
    stateConverter : function (value) {
      var status = util.enumValueToKey(
        CC_OBJECTS.Severity, parseInt(value));
      return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    },
    stateDecoder : function (key) {
      return CC_OBJECTS.Severity[key.toUpperCase()];
    },
    getIconClass : function (value) {
      return 'customIcon icon-severity-' + value.toLowerCase();
    },
    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.severity = null;

      var deferred = new Deferred();
      CC_SERVICE.getSeverityCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, function (res) {
        deferred.resolve(Object.keys(CC_OBJECTS.Severity).sort(
          function (a, b) {
            return CC_OBJECTS.Severity[a] < CC_OBJECTS.Severity[b];
          }).map(function (key) {
            var value = CC_OBJECTS.Severity[key];
            return {
              value : key[0] + key.slice(1).toLowerCase(),
              count : res[value] !== undefined ? res[value] : 0
            };
          }));
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });

      return deferred;
    }
  });
});
