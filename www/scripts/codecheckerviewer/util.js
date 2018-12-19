// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/date/locale',
  'dojo/dom-construct',
  'dojo/dom-style',
  'dojo/json'],
function (locale, dom, style, json) {
  var MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  var tooltips = {
    detectionStatus : "Detection statuses are calculated based on the "
                    + "detection status values from the previous store where "
                    + "the reports are stored again with the same run name. "
                    + "When storing the results of a run from scratch then "
                    + "each report will have detection status of 'New'.",
    numOfUnresolved : "Number of non unique reports excluding Resolved, Off, "
                    + "Unavailable, False positive and Intentional reports",
    versionTag      : "Latest version tag of this run."
  };

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
     * Removes duplications from the given array.
     */
    arrayUnique : function (arr) {
      for (var i = 0; i < arr.length; ++i)
        for(var j = i + 1; j < arr.length; ++j)
          if (arr[i] === arr[j])
            arr.splice(j--, 1);

      return arr;
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

      for (var key in CC_OBJECTS.Severity)
        if (CC_OBJECTS.Severity[key] === parseInt(severityCode))
          return key.toLowerCase();
    },

    /**
     * Converts a Thrift API diff type to human readable string.
     *
     * @param {String|Number} diffType Thrift API DiffType id
     * @return Human readable diff type string.
     */
    diffTypeFromCodeToString : function (diffType) {
      switch (parseInt(diffType)) {
        case CC_OBJECTS.DiffType.NEW:
          return 'New';
        case CC_OBJECTS.DiffType.RESOLVED:
          return 'Resolved';
        case CC_OBJECTS.DiffType.UNRESOLVED:
          return 'Unresolved';
        default:
          console.warn('Non existing diff type code: ', diffType);
          return 'Unknown';
      }
    },

    /**
     * Converts a Thrift API ExtendedReportDataType to human readable string.
     *
     * @param {String|Number} extendedDataType Thrift API
     * ExtendedReportDataType id.
     * @return Human readable report extended data type string.
     */
    reportExtendedTypeFromCodeToString : function (extendedDataType) {
      switch (parseInt(extendedDataType)) {
        case CC_OBJECTS.ExtendedReportDataType.MACRO:
          return 'Macro';
        case CC_OBJECTS.ExtendedReportDataType.NOTE:
          return 'Note';
        case CC_OBJECTS.ExtendedReportDataType.FIXIT:
          return 'Fixit';
        default:
          console.warn('Non existing report extended data code: ',
            extendedDataType);
          return 'Unknown';
      }
    },

    /**
     * This function creates a hexadecimal color from a string.
     */
    strToColor : function (str) {
      var hash = 0;
      for (var i = 0; i < str.length; i++)
         hash = str.charCodeAt(i) + ((hash << 5) - hash);

      var c = (hash & 0x00FFFFFF).toString(16).toUpperCase();

      return '#' + '00000'.substring(0, 6 - c.length) + c;
    },

    /**
     * This function creates a colour from a string, then blend it with the
     * given other colour with the given ratio.
     *
     * @param blendColour a variable applicable to the constructor of
     * dojo.Color. It can be a color name, a hex string, or an array of RGB.
     */
    strToColorBlend : function (str, blendColour, ratio) {
      if (ratio === undefined) {
        ratio = 0.75;
      }

      var baseColour = new dojo.Color(this.strToColor(str));
      return dojo.blendColors(baseColour, new dojo.Color(blendColour), ratio);
    },

    generateRedGreenGradientColor : function (value, max, opacity) {
      var red   = (255 * value) / max;
      var green = (255 * (max - value)) / max;
      var blue  = 0;
      return 'rgba(' + parseInt(red) + ',' + parseInt(green) + ',' + blue
       + ',' + opacity + ')';
    },

    getBugPathLenColor : function (length, bugPathLengthLimit) {
      // This value says that bug path length with this value and above are
      // difficult to understand. The background color of these bug path lengths
      // will be red.
      if (bugPathLengthLimit === undefined)
        bugPathLengthLimit = 20;

      return this.generateRedGreenGradientColor(length,
        bugPathLengthLimit, 0.5);
    },

    /**
     * Converts the given number of seconds into a more human-readable
     * 'hh:mm:ss' format.
      */
    prettifyDuration: function (seconds) {
      var prettyDuration = "--------";

      if (seconds >= 0) {
        var durHours = Math.floor(seconds / 3600);
        var durMins  = Math.floor(seconds / 60) - durHours * 60;
        var durSecs  = seconds - durMins * 60 - durHours * 3600;

        var prettyDurHours = (durHours < 10 ? '0' : '') + durHours;
        var prettyDurMins  = (durMins  < 10 ? '0' : '') + durMins;
        var prettyDurSecs  = (durSecs  < 10 ? '0' : '') + durSecs;

        prettyDuration
          = prettyDurHours + ':' + prettyDurMins + ':' + prettyDurSecs;
      }

      return prettyDuration;
    },

    prettifyDate: function (date) {
      if (!date.length) return "--------";

      var items = date.split(/[\s\.]+/);
      return items[0] + ' ' + items[1];
    },

    /**
     * Creates a human friendly relative time ago on the date.
     */
    timeAgo : function (date) {
      var delta = Math.round((+new Date - date) / 1000);

      var minute = 60,
          hour   = minute * 60,
          day    = hour * 24,
          week   = day * 7,
          month  = day * 30;

      var fuzzy;

      if (delta < 30) {
        fuzzy = 'just now.';
      } else if (delta < minute) {
        fuzzy = delta + ' seconds ago.';
      } else if (delta < 2 * minute) {
        fuzzy = 'a minute ago.'
      } else if (delta < hour) {
        fuzzy = Math.floor(delta / minute) + ' minutes ago.';
      } else if (Math.floor(delta / hour) == 1) {
        fuzzy = '1 hour ago.'
      } else if (delta < day) {
        fuzzy = Math.floor(delta / hour) + ' hours ago.';
      } else if (delta < day * 2) {
        fuzzy = 'yesterday';
      } else if (delta < week) {
        fuzzy = Math.floor(delta / day) + ' days ago.';
      } else if (delta < day * 8) {
        fuzzy = '1 week ago.';
      } else if (delta < month) {
        fuzzy = Math.floor(delta / week) + ' weeks ago.';
      } else {
        fuzzy = 'on ' + locale.format(date, "yyyy-MM-dd HH:mm");
      }

      return fuzzy;
    },

    /**
     * Converts a Thrift API review status id to human readable string.
     *
     * @param {String|Number} reviewCode Thrift API ReviewStatus id.
     * @return Human readable review status string.
     */
    reviewStatusFromCodeToString : function (reviewCode) {
      switch (parseInt(reviewCode)) {
        case CC_OBJECTS.ReviewStatus.UNREVIEWED:
          return 'Unreviewed';
        case CC_OBJECTS.ReviewStatus.CONFIRMED:
          return 'Confirmed';
        case CC_OBJECTS.ReviewStatus.FALSE_POSITIVE:
          return 'False positive';
        case CC_OBJECTS.ReviewStatus.INTENTIONAL:
          return "Intentional";
        default:
          console.error('Non existing review status code: ', reviewCode);
      }
    },

    /**
     * Converts a Thrift API detection status id to human readable string.
     *
     * @param {String|Number} reviewCode Thrift API DetectionStatus id.
     * @return Human readable review status string.
     */
    detectionStatusFromCodeToString : function (detectionStatus) {
      switch (parseInt(detectionStatus)) {
        case CC_OBJECTS.DetectionStatus.NEW:
          return 'New';
        case CC_OBJECTS.DetectionStatus.RESOLVED:
          return 'Resolved';
        case CC_OBJECTS.DetectionStatus.UNRESOLVED:
          return 'Unresolved';
        case CC_OBJECTS.DetectionStatus.REOPENED:
          return 'Reopened';
        case CC_OBJECTS.DetectionStatus.OFF:
          return 'Off';
        case CC_OBJECTS.DetectionStatus.UNAVAILABLE:
          return 'Unavailable';
        default:
          console.error(
            'Non existing detection status code: ',
            detectionStatus);
      }
    },

    /**
     * Converts a Thrift API database status id to human readable string.
     *
     * @param {String|Number} dbStatus Thrift API DBStatus id.
     * @return Human readable review status string.
     */
    dbStatusFromCodeToString : function (dbStatus) {
      switch (parseInt(dbStatus)) {
        case DBStatus.OK:
          return 'Database is up to date.';
        case DBStatus.MISSING:
          return 'Database is missing.';
        case DBStatus.FAILED_TO_CONNECT:
          return 'Failed to connect to the database.';
        case DBStatus.SCHEMA_MISMATCH_OK:
          return 'Schema mismatch: migration is possible.';
        case DBStatus.SCHEMA_MISMATCH_NO:
          return 'Schema mismatch: migration not available.';
        case DBStatus.SCHEMA_MISSING:
          return 'Schema is missing.';
        case DBStatus.SCHEMA_INIT_ERROR:
          return 'Schema initialization error.';
        default:
          console.warn(
            'Non existing database status code: ',
            dbStatus);
          return 'N/A';
      }
    },


    /**
     * Creates a CSS class for a Thrift API review status id.
     *
     * @param {String|Number} reviewCode Thrift API ReviewStatus id.
     * @return CSS class name.
     */
    reviewStatusCssClass : function (reviewCode) {
      var status = this.reviewStatusFromCodeToString(reviewCode);
      return 'review-status-'
        + status.replace(/[^a-zA-Z ]/g, "").toLowerCase().replace(' ', '-');
    },

    /**
     * Creates an avatar for the given name.
     * @param name {String} Author name.
     */
    createAvatar : function (name) {
      var avatar = dom.create('div', { class : 'avatar'});
      style.set(avatar, 'background-color', this.strToColor(name));

      dom.create('div', {
        class : 'avatar-content',
        innerHTML: name.charAt(0).toUpperCase()
      }, avatar);

      return avatar;
    },

    /**
     * Creates a version tag for the given run.
     * @param runName {string} - Name of the run.
     * @param tag {string} - Tag of the run.
     */
    createRunTag : function (runName, tag, tooltip) {
      if (!tag) return;

      if (tooltip === undefined)
        tooltip = 'Version tag';

      var tagWrapper =
        dom.create('span', { class : 'tag-wrapper', title: tooltip });

      dom.create('span', {
        class : 'customIcon tag',
        style : 'color:' + this.strToColor(runName + ':' + tag)
      }, tagWrapper);
      dom.create('span', { class : 'tag', innerHTML : tag }, tagWrapper);

      return tagWrapper;
    },

    /**
     * Creates a dom element for review status tooltip.
     * param review {Object} Thrift ReviewData object.
     */
    reviewStatusTooltipContent : function (review) {
      var content = dom.create('div', { class : 'review-comment-tooltip' });

      var header = dom.create('div', { class : 'header'}, content);

      //--- Avatar ---//
      var avatar = this.createAvatar(review.author);
      dom.place(avatar, header);

      //--- Review author ---//

      dom.create('span', { class : 'author', innerHTML: review.author }, header);

      dom.create('span', { innerHTML: 'changed status' }, header);

      //--- Review time ---//

      var time = this.timeAgo(new Date(review.date));
      dom.create('span', { class : 'time', innerHTML: time }, header);

      //--- Review comment ---//

      dom.create('span', {
        class : 'time',
        innerHTML: review.comment.replace(/(?:\r\n|\r|\n)/g, '<br />')
      }, content);

      return content;
    },

    /**
     * Convert the given enum type's member value (a number) into it's key
     * string.
     */
    enumValueToKey : function (enumType, value) {
      for (var key in enumType)
        if (enumType[key] === value)
          return key;

      return null;
    },

    /**
     * Converts the given string containing Unicode characters to a base64
     * string.
     */
    utoa : function(ustring) {
      return window.btoa(unescape(encodeURIComponent(ustring)));
    },

    /**
     * Converts the given Base64-encoded string to a Unicode string, properly
     * handling the wider codepoints.
     *
     * (Normal "atob" would convert base64 to string where each character
     * is one byte long, chopping up Unicode.)
     */
    atou : function(b64) {
      return decodeURIComponent(escape(window.atob(b64)));
    },

    /**
     * Create permission API parameter string for the given values.
     */
    createPermissionParams : function (values) {
      return json.stringify(values);
    },

    /**
     * Get string representation of the month.
     * @param {number} month - The month (from 0-11).
     */
    getMonthName : function (month) {
      return MONTH_NAMES[month];
    },

    /**
     * Format a date to an AM/PM format.
     * @param {Date} date - date which will be converted.
     */
    formatDateAMPM : function (date) {
      var hours = date.getHours();
      var minutes = date.getMinutes();
      var ampm = hours >= 12 ? 'PM' : 'AM';

      hours = hours % 12;
      hours = hours ? hours : 12;
      minutes = minutes < 10 ? '0' + minutes : minutes;

      return hours + ':' + minutes + ' ' + ampm;
    },

    /**
     * Converts a date to an UTC format timestamp.
     * @param {Date} date - date which will be converted.
     */
    dateToUTCTime : function (date) {
      return Date.UTC(
        date.getUTCFullYear(),
        date.getUTCMonth(),
        date.getUTCDate(),
        date.getUTCHours(),
        date.getUTCMinutes(),
        date.getUTCSeconds(),
        date.getUTCMilliseconds());
    },

    exportToCSV : function (filename, content) {
      var csvContent = 'data:text/csv;charset=utf-8,';
      content.forEach(function (c) {
        csvContent += c.join(',') + '\r\n';
      });

      var link = dom.create('a', {
        href : encodeURI(csvContent),
        download : filename
      }, document.body);

      link.click();
      document.body.removeChild(link);
    },

    createLabelForUniqueCheckbox : function (uniqueCheckBox) {
      return dom.create('label', {
        for : uniqueCheckBox.get('id'),
        innerHTML : 'Unique reports <i class="icon-help"></i>',
        title : 'This narrows the report list to unique bug. The same bug may '
          + 'appear several times if it is found on different control paths, '
          + 'i.e. through different function calls. By checking '
          + '"Unique reports" a report appears only once even if it is found '
          + 'on several paths.'
      }, uniqueCheckBox.domNode, 'after');
    },

    getTooltip : function (name) {
      return tooltips[name] ? tooltips[name] : '';
    }
  };
});
