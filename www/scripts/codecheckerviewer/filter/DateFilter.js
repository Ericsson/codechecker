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

      this.selectedItem = null;
    },

    // Being called when date filter is changed.
    filterChanged : function () {
      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    getIconClass : function (value) {
      switch (value.toLowerCase()) {
        case 'today':
          return 'customIcon text-icon today';
        case 'yesterday':
          return 'customIcon text-icon yesterday';
      }
    },

    getItems : function () {
      var deferred = new Deferred();

      deferred.resolve([
        { value : 'Today' },
        { value : 'Yesterday' }
      ]);

      return deferred;
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
    setDayInterval : function (date) {
      date.setHours(0,0,0,0);

      this._fromDate.set('value', date, false);
      this._fromTime.set('value', date);

      var midnight = date;
      midnight.setHours(23,59,59,0);
      this._toDate.set('value', midnight, false);
      this._toTime.set('value', midnight);

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    select : function (value) {
      if (this.selectedItem)
        this._filterTooltip.deselect(this.selectedItem);

      switch (value.toLowerCase()) {
        case 'today':
          this.setDayInterval(new Date());
          this.selectedItem = value;
          break;
        case 'yesterday':
          var yesterday = new Date();
          yesterday.setDate(yesterday.getDate() - 1);
          this.setDayInterval(yesterday);
          this.selectedItem = value;
          break;
        default:
          console.warn("Value '" + value + "' is not handled!");
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
