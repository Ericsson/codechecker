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
        CC_OBJECTS.ReviewStatus, parseInt(value)).replace('_', ' ');
      return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    },
    stateDecoder : function (key) {
      return CC_OBJECTS.ReviewStatus[key.replace(' ', '_').toUpperCase()];
    },
    defaultValues : function () {
      var state = {};
      state[this.class] = [
        CC_OBJECTS.ReviewStatus.UNREVIEWED,
        CC_OBJECTS.ReviewStatus.CONFIRMED
      ].map(this.stateConverter);

      return state;
    },
    getIconClass : function (value) {
      var statusCode = this.stateDecoder(value);
      return 'customIcon ' + util.reviewStatusCssClass(statusCode);
    },
    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.reviewStatus = null;

      var deferred = new Deferred();
      CC_SERVICE.getReviewStatusCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, function (res) {
        deferred.resolve(Object.keys(CC_OBJECTS.ReviewStatus).map(
          function (key) {
            var value = CC_OBJECTS.ReviewStatus[key];
            return {
              value : util.reviewStatusFromCodeToString(value),
              count : res[value] !== undefined ? res[value] : 0
            };
        }));
      });
      return deferred;
    }
  });
});
