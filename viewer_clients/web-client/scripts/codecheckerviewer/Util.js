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


  severityFromStringToCode : function(severityString) {
    return Severity[severityString.toUpperCase()];
  }


});});
