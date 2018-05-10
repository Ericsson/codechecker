// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/dom-class',
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter',
  'codechecker/util'],
function (dom, domClass, declare, Deferred, SelectFilter, util) {
  return declare(SelectFilter, {
    notAvailableMsg : 'Not available in uniqueing mode! Several detection '
                    + 'statuses could belong to the same bug!',

    postCreate : function () {
      this.inherited(arguments);

      this._notAvailable = dom.create('i', {
        class : 'customIcon warn hide',
        title : this.notAvailableMsg
      }, this._title, 'after');
    },

    stateConverter : function (value) {
      var status = util.enumValueToKey(
        CC_OBJECTS.DetectionStatus, parseInt(value));
      return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    },
    stateDecoder : function (key) {
      return CC_OBJECTS.DetectionStatus[key.toUpperCase()];
    },
    defaultValues : function () {
      var state = {};
      state[this.class] = [
        CC_OBJECTS.DetectionStatus.NEW,
        CC_OBJECTS.DetectionStatus.REOPENED,
        CC_OBJECTS.DetectionStatus.UNRESOLVED
      ].map(this.stateConverter);

      return state;
    },
    getIconClass : function (value) {
      return 'customIcon detection-status-' + value.toLowerCase();
    },
    getItems : function (opt) {
      opt = this.parent.initReportFilterOptions(opt);
      opt.reportFilter.detectionStatus = null;

      var deferred = new Deferred();

      if (opt.reportFilter.isUnique) {
        var count = '<span title="' + this.notAvailableMsg + '">N/A</span>'
        return deferred.resolve(Object.keys(CC_OBJECTS.DetectionStatus).map(
        function (key) {
          var value = CC_OBJECTS.DetectionStatus[key];
          return {
            value : util.detectionStatusFromCodeToString(value),
            count : count
          };
        }));
      }

      CC_SERVICE.getDetectionStatusCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, function (res) {
        deferred.resolve(Object.keys(CC_OBJECTS.DetectionStatus).map(
          function (key) {
            var value = CC_OBJECTS.DetectionStatus[key];
            return {
              value : util.detectionStatusFromCodeToString(value),
              count : res[value] !== undefined ? res[value] : 0
            };
        }));
      });
      return deferred;
    },

    notAvailable : function () {
      domClass.remove(this._notAvailable, 'hide');
    },

    available : function () {
      domClass.add(this._notAvailable, 'hide');
    },
  });
});
