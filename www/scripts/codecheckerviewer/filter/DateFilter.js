// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'dojo/dom-construct',
  'dijit/form/DateTextBox',
  'dijit/form/TimeTextBox',
  'codechecker/filter/SelectFilter',
  'codechecker/util'],
function (declare, Deferred, dom, DateTextBox, TimeTextBox, SelectFilter,
  util) {

  // Date types which will be added to the Date filter tooltip.
  var DATE_FILTER_ITEMS = {
    'TODAY' : 0,
    'YESTERDAY' : 1,
    'LAST_7_DAYS' : 2,
    'THIS_MONTH' : 3,
    'THIS_YEAR' : 4
  };

  // Gets Date interval for a date filter type.
  function getDateFilterInteval(type) {
    switch (type) {
      case DATE_FILTER_ITEMS.TODAY:
        var midnight = new Date();
        midnight.setHours(23,59,59,0);
        return { from : new Date(), to : midnight};
      case DATE_FILTER_ITEMS.YESTERDAY:
        var yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);

        var yesterdayMidnight = new Date(yesterday);
        yesterdayMidnight.setHours(23,59,59,0);

        return { from : yesterday, to : yesterdayMidnight};
      case DATE_FILTER_ITEMS.LAST_7_DAYS:
        var today = new Date();
        var lastSevenDays = new Date(today.setDate(today.getDate() - 7));

        return { from : lastSevenDays, to : new Date()};
      case DATE_FILTER_ITEMS.THIS_MONTH:
        var today = new Date();
        var startDate = new Date(today.getFullYear(), today.getMonth(), 1);
        return { from : startDate, to : today};
      case DATE_FILTER_ITEMS.THIS_YEAR:
        var today = new Date();
        var startDate = new Date(today.getFullYear(), 0, 1);
        return { from : startDate, to : today};
      default:
        console.warn("No date interval has been specified for type: " + type);
    }
  }

  // Returns human readable date format for the given date inteval.
  // E.g.:
  // 1.) Months are different: 1 January - 9 March, 2018
  // 2.) Months are same:      March 1 - 9, 2018
  function formatDateInterval (fromDate, toDate) {
    var from = fromDate.getDate();
    var to = toDate.getDate();
    if (fromDate.getMonth() !== toDate.getMonth()) {
      from += ' ' + util.getMonthName(fromDate.getMonth());
      to   += ' ' + util.getMonthName(toDate.getMonth());
    } else
      from = util.getMonthName(fromDate.getMonth()) + ' '  + from;

    if (fromDate.getFullYear() !== toDate.getFullYear()) {
      from += ' ' + fromDate.getFullYear();
      to   += ' ' + toDate.getFullYear();
    } else
      to += ', ' + fromDate.getFullYear();

    return from + ' - ' + to;
  }

  return declare(SelectFilter, {
    postCreate : function () {
      var that = this;

      // Initalize the header of the filter.
      this.initHeader();

      //--- From date time section. ---//

      this._fromDate = new DateTextBox({
        class : 'first-detection-date',
        placeholder : 'Detection date...',
        constraints : { datePattern : 'yyyy-MM-dd' },
        promptMessage : 'yyyy-MM-dd',
        invalidMessage: 'Invalid date format. Use yyyy-MM-dd',
        onChange : function (state) {
          that.filterChanged();
        }
      });

      this._fromTime = new TimeTextBox({
        class : 'first-detection-time',
        constraints: {
          timePattern: 'HH:mm:ss'
        },
        onChange : function () {
          if (that._fromDate.get('displayedValue'))
            that.filterChanged();
        }
      });

      //--- To date time section. ---//

      this._toDate = new DateTextBox({
        class : 'fix-date',
        placeholder : 'Fixed date...',
        constraints : { datePattern : 'yyyy-MM-dd' },
        promptMessage : 'yyyy-MM-dd',
        invalidMessage: 'Invalid date format. Use yyyy-MM-dd',
        onChange : function (state) {
          that.filterChanged();
        }
      });

      this._toTime = new TimeTextBox({
        class : 'fix-time',
        constraints: {
          timePattern: 'HH:mm:ss'
        },
        onChange : function () {
          if (that._fromDate.get('displayedValue'))
            that.filterChanged();
        }
      });

      //--- Add items to the DOM. ---//

      var fromDateWrapper =
        dom.create('div', { class : 'date-wrapper' }, this.domNode);

      dom.place(this._fromDate.domNode, fromDateWrapper);
      dom.place(this._fromTime.domNode, fromDateWrapper);

      var toDateWrapper =
        dom.create('div', { class : 'date-wrapper' }, this.domNode);

      dom.place(this._toDate.domNode, toDateWrapper);
      dom.place(this._toTime.domNode, toDateWrapper);
    },

    // Being called when date filter is changed.
    filterChanged : function () {
      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
      this.notifyOthers();
    },

    getIconClass : function (value) {
      var key = util.enumValueToKey(DATE_FILTER_ITEMS, value);
      if (key)
        return 'customIcon text-icon ' + key.split('_').join('-').toLowerCase();
    },

    labelFormatter : function (value) {
      var interval = getDateFilterInteval(value);

      var formattedDate = interval
        ? formatDateInterval(interval.from, interval.to)
        : 'N/A';

      switch (value) {
        case DATE_FILTER_ITEMS.TODAY:
          return 'Today';
        case DATE_FILTER_ITEMS.YESTERDAY:
          return 'Yesterday';
        case DATE_FILTER_ITEMS.LAST_7_DAYS:
          return 'Last 7 days (' + formattedDate + ')';
        case DATE_FILTER_ITEMS.THIS_MONTH:
          return 'This month (' + formattedDate + ')';
        case DATE_FILTER_ITEMS.THIS_YEAR:
          return 'This year (' + formattedDate + ')';
        default:
          return value;
      }
    },

    getItems : function () {
      var deferred = new Deferred();

      var items = [];
      for (var key in DATE_FILTER_ITEMS)
        items.push({ value : DATE_FILTER_ITEMS[key] });

      return deferred.resolve(items);
    },

    getUrlState : function () {
      var state = {};

      var fromDate = this._fromDate.get('displayedValue');
      var fromTime = this._fromTime.get('displayedValue');
      state[this._fromDate.class] = fromDate ? fromDate + ' ' + fromTime : null;

      var toDate = this._toDate.get('displayedValue');
      var toTime = this._toTime.get('displayedValue');
      state[this._toDate.class] = toDate ? toDate + ' ' + toTime : null;

      return state;
    },

    initByUrl : function (queryParams) {
      this.initDetectedAtInterval(queryParams[this._fromDate.class]);
      this.initFixedDateInterval(queryParams[this._toDate.class]);

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    // Initalize the detected at date time.
    initDetectedAtInterval : function (detectedAt) {
      if (!detectedAt) {
        this._fromDate.set('value', null , false);
        this._fromTime.set('value', null, false);
        return;
      }

      var date = new Date(detectedAt);
      date.setMilliseconds(0);

      this._fromDate.set('value', date , false);
      this._fromTime.set('value', date, false);
    },

    // Initalize the fixed at date time.
    initFixedDateInterval : function (fixedAt) {
      if (!fixedAt) {
        this._toDate.set('value', null , false);
        this._toTime.set('value', null, false);
        return;
      }

      var date = new Date(fixedAt);
      date.setMilliseconds(0);

      this._toDate.set('value', date , false);
      this._toTime.set('value', date, false);
    },

    // Returns UTC timestamp of the parameter.
    getTimeStamp : function (dateTime) {
      if (dateTime) {
        var fullDate = new Date(dateTime);
        if (!isNaN(fullDate))
          return util.dateToUTCTime(fullDate) / 1000;
      }
      return null;
    },

    getSelectedItemValues : function () {
      var state = this.getUrlState();
      return {
        detectionDate : this.getTimeStamp(state[this._fromDate.class]),
        fixDate : this.getTimeStamp(state[this._toDate.class]),
      };
    },

    // Set whole day interval of the detected and fixed date filters.
    setDayInterval : function (fromDate, toDate) {
      fromDate.setHours(0,0,0,0);

      this._fromDate.set('value', fromDate, false);
      this._fromTime.set('value', fromDate);

      if (toDate === undefined) {
        toDate = fromDate;
        toDate.setHours(23,59,59,0);
      }

      this._toDate.set('value', toDate, false);
      this._toTime.set('value', toDate);

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    select : function (value) {
      this._filterTooltip.deselectAll();

      var key = util.enumValueToKey(DATE_FILTER_ITEMS, value);
      if (key) {
        var interval = getDateFilterInteval(value);
        if (!interval) return;

        this.setDayInterval(interval.from, interval.to);
      } else {
        console.warn("Value '" + key + "' is not handled!");
      }
    },

    clear : function () {
      this._fromDate.set('value', null, false);
      this._fromTime.set('value', null, false);

      this._toDate.set('value', null, false);
      this._toTime.set('value', null, false);

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    // Override this inherited function because we do not need to update
    // anything on other filter changes (we do not count reports for these
    // filter items).
    notify : function () {}
  });
});
