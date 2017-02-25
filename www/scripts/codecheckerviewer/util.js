// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([],
function () {
  return {
    /**
     * This function returns the first element of the given array for which the
     * given function gives true. There is a find() function in JavaScript
     * which can be invoked for arrays, but that is not supported by older
     * browsers.
     */
    findInArray : function (arr, func) {
      for (var i = 0, len = arr.length; i < len; ++i)
        if (func(arr[i]))
          return arr[i];
    },

    /**
     * This function returns the index of the first element in the given array
     * for which the given function gives true. If the element is not found,
     * then it returns -1. There is a findIndex() function in JavaScript which
     * can be invoked for array, but that is not supported by older browsers.
     */
    findIndexInArray : function (arr, func) {
      for (var i = 0, len = arr.length; i < len; ++i)
        if (func(arr[i]))
          return i;
      return -1;
    },

    /**
     * Converts a Thrift API severity id to human readable string.
     *
     * @param {String|Number} severityCode Thrift API Severity id
     * @return Human readable severity string.
     */
    severityFromCodeToString : function (severityCode) {
      if (severityCode === 'all')
        return 'All';

      for (var key in Severity)
        if (Severity[key] === parseInt(severityCode))
          return key.toLowerCase();
    }
  };
});
