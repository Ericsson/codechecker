// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
], function ( declare ) {
  /**
   * This class contains various utility functions. It is instanciated once in
   * the global namespace as CC_UTIL
   */
return declare(null, {



  /**
   * Queries the available severity types for checkers
   */
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


  /**
   * Queries the available checkers and selects those which are found in the
   * appropriate run.
   */
  getAvailableCheckers : function(overviewTC) {
    var checkerTypeOptionsArray = [ { value: "*", label: "All checkers" , selected: true } ];

    if (overviewTC.overviewType === "run") {

      CC_SERVICE.getRunResultTypes(overviewTC.runId, [], function(resultTypes) {
        resultTypes.forEach(function(item) {
          checkerTypeOptionsArray.push( { value: item.checkerId + "", label: item.checkerId + "" } );
        });
      });

    } else if (overviewTC.overviewType === "diff") {

      CC_SERVICE.getRunResultTypes(overviewTC.runId1, [], function(resultTypes1) {
        CC_SERVICE.getRunResultTypes(overviewTC.runId2, [], function(resultTypes2) {
          var temp = {};

          resultTypes1.forEach(function(item) {
            temp[item.checkerId] = true;
          });

          resultTypes2.forEach(function(item) {
            temp[item.checkerId] = true;
          });

          for (var elem in temp) {
            checkerTypeOptionsArray.push( { value: elem + "", label: elem + "" } );
          }

        });
      });

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
