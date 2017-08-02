// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/date/locale',
  'dojo/dom-construct',
  'dojo/dom-style'],
function (locale, dom, style) {
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
     * Creates a human friendly relative time ago on the date.
     */
    timeAgo : function (date) {
      var delta = Math.round((+new Date - date) / 1000);

      var minute = 60,
          hour   = minute * 60,
          day    = hour * 24,
          week   = day * 7,
          month  = day * 30
          year   = day * 365;

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
        case ReviewStatus.UNREVIEWED:
          return 'Unreviewed';
        case ReviewStatus.CONFIRMED:
          return 'Confirmed bug';
        case ReviewStatus.FALSE_POSITIVE:
          return 'False positive';
        case ReviewStatus.WONT_FIX:
          return "Won't fix";
        default:
          console.error('Non existing review status code: ', reviewCode);
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
      return status.replace(/[^a-zA-Z ]/g, "").toLowerCase().replace(' ', '-');
    },

    /**
     * Creates an avatar for the given name.
     * @param name {String} Author name.
     */
    createAvatar : function (name) {
      var avatar = dom.create('div', { class : 'avatar'});
      style.set(avatar, 'background-color', this.strToColor(name));

      var avatarLabel = name.charAt(0).toUpperCase();
      var avatarContent = dom.create('div', {
        class : 'avatar-content', innerHTML: avatarLabel }, avatar);

      return avatar;
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

      var message = dom.create('span', {
        class : 'time',
        innerHTML: review.comment.replace(/(?:\r\n|\r|\n)/g, '<br />')
      }, content);

      return content;
    }
  };
});
