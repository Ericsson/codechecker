// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
], function ( declare ) {
return declare(null, {


  getAvailableSeverityLevels : function() {
    var severityLevelTypeOptionsArray = [];

    for (var key in Severity){
      var severityStringLowerCase = key.toLowerCase();
      var severityString = severityStringLowerCase.charAt(0).toUpperCase() + severityStringLowerCase.slice(1);
      var severityCode   = Severity[key];

      severityLevelTypeOptionsArray.unshift( { value: severityCode + "", label: severityString + "" } );
    }

    severityLevelTypeOptionsArray.unshift( { value: "all", label: "All" , selected: true } );

    return severityLevelTypeOptionsArray;
  },


  getAvailableCheckers : function(overviewTC) {
    var temp = {};

    if (overviewTC.overviewType === "run") {

      var resultTypes = CC_SERVICE.getRunResultTypes(overviewTC.runId, []);

      for (var i = 0 , len = resultTypes.length ; i < len; ++i) {
        temp[resultTypes[i].checkerId] = true;
      }

    } else if (overviewTC.overviewType === "diff") {

      var resultTypes1 = CC_SERVICE.getRunResultTypes(overviewTC.runId1, []);
      var resultTypes2 = CC_SERVICE.getRunResultTypes(overviewTC.runId2, []);

      for (var i = 0 , len = resultTypes1.length ; i < len; ++i) {
        temp[resultTypes1[i].checkerId] = true;
      }

      for (var i = 0 , len = resultTypes2.length ; i < len; ++i) {
        temp[resultTypes2[i].checkerId] = true;
      }

    }

    var checkerTypeOptionsArray = [ { value: "*", label: "All checkers" , selected: true } ];

    for (var elem in temp) {
      checkerTypeOptionsArray.push( { value: elem + "", label: elem + "" } );
    }

    return checkerTypeOptionsArray;
  },

  /**
   * Converts a Thrift API severity id to human readable string.
   *
   * @param severityCode Thrift API severity id
   * @return human readable severity string
   */
  severityFromCodeToString : function(severityCode) {
    if (severityCode === "all"){
      return "All"
    }

    for (var key in Severity) {
      if (Severity[key] === parseInt(severityCode)){
        return key.toLowerCase();
      }
    }

    return null;
  },

  /**
   * Converts a severity string to Thrift API severity id.
   *
   * @param severityString severity as string
   * @return severity as number (id)
   */
  severityFromStringToCode : function(severityString) {
    return Severity[severityString.toUpperCase()];
  },

  /**
   * Returns overview DOM id for the given browser hash state.
   *
   * @param hashState browser hash state object
   * @return DOM id string or undefined
   */
  getOverviewIdFromHashState : function(hashState) {
    if (hashState.ovType == 'run') {
      return "runoverviewtc_" + hashState.ovRunId;
    } else if (hashState.ovType == 'diff') {
      return "diffoverviewtc_" + hashState.diffRunIds[0] + "_" +  hashState.diffRunIds[1];
    } else if (JSON.stringify(hashState) == "{}") {
      return "bc_listofrunsgrid";
    }

    return undefined;
  }
});});
