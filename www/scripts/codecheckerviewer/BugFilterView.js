// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'dojo/dom-construct',
  'dojo/dom-class',
  'dojo/promise/all',
  'dojo/topic',
  'dojox/widget/Standby',
  'dijit/form/Button',
  'dijit/form/CheckBox',
  'dijit/form/DateTextBox',
  'dijit/form/TextBox',
  'dijit/form/TimeTextBox',
  'dijit/popup',
  'dijit/TooltipDialog',
  'dijit/layout/ContentPane',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, Deferred, dom, domClass, all, topic, Standby, Button,
  CheckBox, DateTextBox, TextBox, TimeTextBox, popup, TooltipDialog,
  ContentPane, hashHelper, util) {

  function alphabetical(a, b) {
    if (a < b) return -1;
    if (a > b) return 1;

    return 0;
  }

  /**
   * Selected filter item which will be shown at the sidebar filter pane.
   * @prop {string} label - The label of the filter item. This field is a
   * required property.
   * @prop {string} iconClass - The icon class of the filter item. This property
   * is optional.
   * @prop {integer} count - Number of reports.
   */
  var SelectedFilterItem = declare(ContentPane, {
    postCreate : function () {
      this.inherited(arguments);

      if (this.iconClass)
        var label = dom.create('span', {
          class : this.iconClass,
          style : this.iconStyle
        }, this.domNode);

      this._labelWrapper = dom.create('span', {
        class : 'label',
        title : this.label,
        innerHTML : this.label
      }, this.domNode);

      if (this.count !== undefined) {
        this._countWrapper = dom.create('span', {
          class : 'count',
          innerHTML : this.count
        }, this.domNode);

        if (!this.disableRemove)
          dom.create('span', {
            class : 'customIcon remove'
          }, this.domNode);
      }
    },

    update : function (item) {
      if (this._countWrapper)
        this._countWrapper.innerHTML = item ? item.count : 0;

      if (item) {
        this.item = item;
        this._labelWrapper.innerHTML = item.label;
      }
    }
  });

  /**
   * Creates a tooltip for a report filter with selectable options.
   */
  var FilterTooltip = declare(ContentPane, {
    constructor : function (args) {
      dojo.safeMixin(this, args);

      var that = this;

      this._selectMenuList = dom.create('div', {
        class : 'select-menu-list ' + that.class
      });

      if (this.search && this.search.enable)
        this._searchBox = new TextBox({
          placeholder : this.search.placeHolder,
          class       : 'select-menu-filter',
          onKeyUp     : function () {
            clearTimeout(this.timer);

            var query = this.get('value');
            this.timer = setTimeout(function () {
              dom.empty(that._selectMenuList);
              that._render(query);
            }, 300);
          }
        });
    },

    postCreate : function () {
      if (this.search && this.search.enable)
        this.addChild(this._searchBox);

      dom.place(this._selectMenuList, this.domNode);

      //--- Tooltip dialog ---//

      this._dialog = new TooltipDialog({
        content : this.domNode,
        onBlur : function () {
          popup.close(this);
        }
      });
    },

    /**
     * Shows the tooltip.
     */
    show : function () {
      this._render();

      //--- Open up the tooltip ---//

      popup.open({
        popup : this._dialog,
        around : this.around
      });

      this._dialog.focus();
    },

    _search : function (text, query) {
      return query && text.toLowerCase().indexOf(query.toLowerCase()) === -1;
    },

    /**
     * Creates filter items for a filter.
     * @param widget {widget} - Dojo widget item where the created items will
     * be placed.
     * @param query {string} - Filter query.
     */
    _render : function (query) {
      var that = this;

      dom.empty(this._selectMenuList);

      var skippedList = that.reportFilter.getSkippedValues();

      var hasItem = false;

      this.reportFilter._items.forEach(function (item) {
        if (that._search(item.label, query))
          return;

        hasItem = true;

        var content = '<span class="customIcon selected"></span>'
          + (item.iconClass
             ? '<span class="' + item.iconClass + '" style="' +
               (item.iconStyle ? item.iconStyle : '') + '"></span>'
             : '')
          + '<span class="label">' + item.label + '</span>';

        if (item.count !== undefined)
          content += '<span class="count">' + item.count + '</span>';

        var selected = that.reportFilter._selectedFilterItems &&
          item.value in that.reportFilter._selectedFilterItems;

        var disabled = skippedList.indexOf(item.value.toString()) !== -1;

        if (disabled)
          return;

        dom.create('div', {
          class     : 'select-menu-item ' + (selected ? 'selected' : ''),
          innerHTML : content,
          onclick   : function () {
            if (that.disableMultipleOption) {
              that.reportFilter.clearAll();
              that.reportFilter.selectItem(that.class, item.value);
              that._render();
              return;
            }

            if (that.reportFilter._selectedFilterItems
              && item.value in that.reportFilter._selectedFilterItems) {
              that.reportFilter.deselectItem(item.value);
              domClass.remove(this, 'selected');
            } else {
              that.reportFilter.selectItem(that.class, item.value);
              domClass.add(this, 'selected');
            }

            that._render(query);
          },
          title : item.label
        }, that._selectMenuList);
      });

      if (!hasItem)
        dom.create('div', {
          class     : 'select-menu-item no-item',
          innerHTML : 'No item'
        }, that._selectMenuList);
    }
  });

  var FilterBase = declare(ContentPane, {
    postCreate : function () {
      var that = this;

      //--- Filter header ---//

      this._header = dom.create('div', { class : 'header' }, this.domNode);

      this._title = dom.create('span', {
        class     : 'title',
        innerHTML : this.title
      }, this._header);

      this._options = dom.create('span', { class : 'options' }, this._header);

      if (!that.disableMultipleOption)
        this._clean = dom.create('span', {
          class : 'customIcon clean',
          onclick : function () {
            that.clearAll();

            topic.publish('filterchange', {
              parent : that.parent,
              changed : that.getUrlState()
            });
          }
        }, this._options);

      //--- Loading widget ---//

      this._standBy = new Standby({
        target : this.domNode,
        color : '#ffffff'
      });
      this.addChild(this._standBy);
    },

    /**
     * Converts an item value to human readable format.
     * Let's ReviewStatus = {UNREVIEWED = 0;}. If the value parameter is 0 then
     * it returns with the `unreviewed` string.
     */
    stateConverter : function (value) { return value; },

    /**
     * Get value of the human readable string value of the item.
     * Let's ReviewStatus = {UNREVIEWED = 0;}. If the value parameter is
     * `unreviewed` it returns with the 0.
     */
    stateDecoder : function (value) {
      return isNaN(value) ? value : parseFloat(value);
    },

    /**
     * Returns human readable url state object by calling the state converter
     * function.
     */
    getUrlState : function () {
      var that = this;

      var state = this.getState();
      if (state[this.class])
        state[this.class] = state[this.class].map(function (value) {
          return that.stateConverter(value);
        });

      return state;
    },

    /**
     * Returns the current state of the filter as key-value pair object. The key
     * will be the filter class name and the value will be the selected item
     * values. If no filter item is selected the value will be null.
     */
    getState : function () { return { [this.class] : null }; },

    /**
     * Set filter state from the parameter state object.
     * Returns true if there is any item which is newly selected.
     */
    setState : function (state) { return false; },

    /**
     * Deselecting items which are selected but not in the state parameter.
     */
    deselectByState : function (state) {},

    /**
     * Returns the default values of the filter as key-value pair object.
     * The key identifies the filter and the value is a list of converted
     * human readable values.
     * @see stateConverter
     */
    defaultValues : function () { return {}; },

    loading : function () {
      this._standBy.show();
    },

    loaded : function () {
      this._standBy.hide();
    },

    /**
     * Clears all selected items.
     */
    clearAll : function () {},

    destroy : function () {
      this.inherited(arguments);

      this._standBy.destroyRecursive();
    },

    getSkippedValues : function () { return []; }
  });

  /**
   * Base class of filters.
   * @property title {string} - Title of the filter.
   * @property enableSearch {bool} - Enable search field and the user can query
   * the filter options.
   * @property filterLabel {string} - This text appears in the search field.
   * @function getItems {array} Returns an array of Object which can be
   * selected. The property of an item object can be the following:
   *   @property Object.label {string} - A filter item label which will be
   *   shown in the gui as the filter selection value (required).
   *   @property Object.value {number|boolean} - Filter item value which
   *   uniqually identifies a filter item (required).
   *   @property Object.iconClass {string} - Class names for an icon which will
   *   be shown in the gui beside the label.
   */
  var SelectFilter = declare(FilterBase, {

    constructor : function (args) {
      dojo.safeMixin(this, args);
      this.inherited(arguments);

      var that = this;

      this._selectedFilterItems = {}; // Selected filters values.
      this._selectedValuesCount = 0; // Selected filters count.

      this._selectedFilters = new ContentPane({ class : 'items' });

      this._noFilterItem = new SelectedFilterItem({
        class         : 'select-menu-item none',
        label         : 'No filter'
      });

      this._filterTooltip = new FilterTooltip({
        class : this.class,
        search : {
          enable : this.enableSearch,
          placeHolder : this.filterLabel
        },
        disableMultipleOption : this.disableMultipleOption,
        reportFilter : this
      });
    },

    postCreate : function () {
      this.inherited(arguments);

      var that = this;

      this._edit = dom.create('span', {
        class : 'customIcon edit',
        onclick : function () {
          that._filterTooltip.show();
        }
      }, this._options);

      this._filterTooltip.set('around', this._edit);

      //--- Filter items ---//

      this.addChild(this._selectedFilters);

      //--- No filter enabled ---//

      this._selectedFilters.addChild(this._noFilterItem);
    },

    setState : function (state) {
      var that = this;

      var changed = false;
      var filterState = state[this.class]
        ? state[this.class]
        : [];

      if (!(filterState instanceof Array))
        filterState = [filterState];

      filterState.forEach(function (value) {
        var value = that.stateDecoder(value);

        if (value === null) {
          changed = true;
          return;
        }

        if (!that._selectedFilterItems[value]) {
          that._selectedFilterItems[value] = null;
          changed = true;
        }
      });

      return changed;
    },

    deselectByState : function (state) {
      var that = this;

      var urlFilterState = state[this.class] ? state[this.class] : [];
      if (!(urlFilterState instanceof Array))
        urlFilterState = [urlFilterState];

      var filterState = this.getState()[this.class];
      if (filterState)
        filterState.forEach(function (s) {
          var value = that.stateConverter(s);
          if (urlFilterState.indexOf(value.toString()) === -1) {
            that.deselectItem(s, true);
          }
        });
    },

    getState : function () {
      var state = Object.keys(this._selectedFilterItems).map(function (key) {
        return isNaN(key) ? key : parseFloat(key);
      });

      return  { [this.class] : state.length ? state : null };
    },

    /**
     * Returns a SelectedFilterItem element by value.
     */
    getItem : function (value) {
      var items = this._items.filter(function (item) {
        return item.value == value;
      });

      return items.length ? items[0] : null;
    },

    getSelectedItem : function () {
      var that = this;

      return Object.keys(this._selectedFilterItems).map(function (key) {
        return that._selectedFilterItems[key];
      });
    },

    /**
     * Select a filter item by value.
     * @param key {string} - The name of the selected filter item.
     * @param value {integer|string} - Value of the selected item.
     * @param preventFilterChange - If true it prevents the filter change event.
     */
    selectItem : function (key, value, preventFilterChange) {
      var that = this;

      var item = this.getItem(value);

      if (this.disableMultipleOption && this._selectedValuesCount)
        return;

      // If already selected, update the report counter of the filter:
      // if there isn't any item with this value from the server,
      // we update the counter to zero.
      if (this._selectedFilterItems[value]) {
        this._selectedFilterItems[value].update(item);
        return;
      }

      if (!item)
      {
        item = {
          label : value,
          value : value,
          count : 0
        }
      }

      //--- Remove the No Filter item ---//

      if (!this._selectedValuesCount) {
        this._selectedFilters.getChildren().forEach(function (child) {
          that._selectedFilters.removeChild(child);
        });
      }

      var disableRemove = this.disableMultipleOption;
      this._selectedFilterItems[value] = new SelectedFilterItem({
        class : 'select-menu-item ' + (disableRemove ? 'disabled' : ''),
        label : item.label,
        iconClass : item.iconClass,
        iconStyle : item.iconStyle,
        value : value,
        count : item.count,
        item  : item,
        disableRemove : disableRemove,
        onClick : function () {
          if (!that.disableClear && !disableRemove) {
            that.deselectItem(value);
            this.destroy();
          }
        }
      });

      this._selectedFilters.addChild(this._selectedFilterItems[value]);

      ++this._selectedValuesCount;

      if (!preventFilterChange)
        topic.publish('filterchange', {
          parent : this.parent,
          changed : this.getUrlState()
        });
    },

    /**
     * Deselect a filter item by value.
     * @param value {integer|string} - Value of the deselected item.
     * @param preventFilterChange - If true it prevents the filter change event.
     */
    deselectItem : function (value, preventFilterChange) {
      var item = this._selectedFilterItems[value];

      //--- If doesn't selected, return ---//

      if (!item)
        return;

      //--- Remove the selected item ---//

      this._selectedFilters.removeChild(item);
      delete this._selectedFilterItems[value];

      --this._selectedValuesCount;

      if (!this._selectedValuesCount)
        this._selectedFilters.addChild(this._noFilterItem);

      if (!preventFilterChange) {
        topic.publish('filterchange', {
          parent : this.parent,
          changed : this.getUrlState()
        });
      }
    },

    clearAll : function () {
      for (key in this._selectedFilterItems) {
        var item = this._selectedFilterItems[key];

        if (item)
          this.deselectItem(item.value, true);
        else
          delete this._selectedFilterItems[key];
      }
    }
  });

  var DateFilter = declare(FilterBase, {
    constructor : function () {
      var that = this;

      this._fromDate = new DateTextBox({
        class : 'first-detection-date',
        placeholder : 'Detection date...',
        constraints : { datePattern : 'yyyy-MM-dd' },
        promptMessage : 'yyyy-MM-dd',
        invalidMessage: 'Invalid date format. Use yyyy-MM-dd',
        onChange : function (state) {
          that.onTimeChange();
        }
      });

      this._fromTime = new TimeTextBox({
        class : 'first-detection-time',
        constraints: {
          timePattern: 'HH:mm:ss'
        },
        onChange : function () {
          if (that._fromDate.get('value'))
            that.onTimeChange();
        }
      });

      this._toDate = new DateTextBox({
        class : 'fix-date',
        placeholder : 'Fixed date...',
        constraints : { datePattern : 'yyyy-MM-dd' },
        promptMessage : 'yyyy-MM-dd',
        invalidMessage: 'Invalid date format. Use yyyy-MM-dd',
        onChange : function (state) {
          that.onTimeChange();
        }
      });

      this._toTime = new TimeTextBox({
        class : 'fix-time',
        constraints: {
          timePattern: 'HH:mm:ss'
        },
        onChange : function () {
          if (that._toDate.get('value'))
            that.onTimeChange();
        }
      });

      this._filterTooltip = new FilterTooltip({
        class : this.class,
        reportFilter : this
      });
    },

    postCreate : function () {
      this.inherited(arguments);

      var that = this;

      this._edit = dom.create('span', {
        class : 'customIcon edit',
        onclick : function () {
          that._filterTooltip.show();
        }
      }, this._options);

      this._filterTooltip.set('around', this._edit);

      var fromDateWrapper =
        dom.create('div', { class : 'date-wrapper' }, this.domNode);

      dom.place(this._fromDate.domNode, fromDateWrapper);
      dom.place(this._fromTime.domNode, fromDateWrapper);

      var toDateWrapper =
        dom.create('div', { class : 'date-wrapper' }, this.domNode);

      dom.place(this._toDate.domNode, toDateWrapper);
      dom.place(this._toTime.domNode, toDateWrapper);
    },

    _updateConstrains : function () {
      this._toDate.constraints.min = this._fromDate.get('value');
      this._fromDate.constraints.max = new Date();
    },

    onTimeChange : function () {
      topic.publish('filterchange', {
        parent : this.parent,
        changed : this.getUrlState()
      });
    },

    setToday : function () {
      this._fromDate.set('value', new Date(), false);
      var zero = new Date();
      zero.setHours(0,0,0,0);
      this._fromTime.set('value', zero);

      this._toDate.set('value', new Date(), false);
      var midnight = new Date();
      zero.setHours(23,59,59,0);
      this._toTime.set('value', zero);

      this.onTimeChange();
    },

    setYesterday : function () {
      var yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      yesterday.setHours(0,0,0,0);

      this._fromDate.set('value', yesterday, false);
      this._fromTime.set('value', yesterday);

      var yesterdayMidnight = yesterday;
      yesterdayMidnight.setHours(23,59,59,0);

      this._toDate.set('value', yesterdayMidnight, false);
      this._toTime.set('value', yesterdayMidnight);

      this.onTimeChange();
    },

    getPrevDateTime : function (date, time) {
      var prevDate = date.get('value');
      var prevTime = time.get('value');

      if (!prevDate)
        return null;

      if (prevTime) {
        prevDate.setHours(prevTime.getHours());
        prevDate.setMinutes(prevTime.getMinutes());
        prevDate.setSeconds(prevTime.getSeconds());
      }

      return prevDate;
    },

    selectItem : function (key, value) {
      var changed = false;

      if (value === 'today') {
        this.setToday();
        changed = true;
      } else if (value === 'yesterday') {
        this.setYesterday();
        changed = true;
      } else if (key === 'firstDetectionDate') {
        if (!this._fromTime.get('displayedValue').length) {
          var zero = new Date();
          zero.setHours(0,0,0,0);
          this._fromTime.set('value', zero, false);
        }

        var prevDate = this.getPrevDateTime(this._fromDate, this._fromTime);
        var date = new Date(value);
        date.setMilliseconds(0);

        if (!prevDate || prevDate.getTime() !== date.getTime()) {
          this._fromDate.set('value', date , false);
          this._fromTime.set('value', date);

          changed = true;
        }
      } else if (key === 'fixDate') {
        if (!this._toTime.get('displayedValue').length) {
          var zero = new Date();
          zero.setHours(23,59,59,0);
          this._toTime.set('value', zero, false);
        }

        var prevDate = this.getPrevDateTime(this._toDate, this._toTime);
        var date = new Date(value);
        date.setMilliseconds(0);

        if (!prevDate || prevDate.getTime() !== date.getTime()) {
          this._toDate.set('value', date, false);
          this._toTime.set('value', date);

          changed = true;
        }
      }

      this._updateConstrains();
      return changed;
    },

    setState : function (state) {
      var changed = false;
      var from = state[this._fromDate.class];
      var to   = state[this._toDate.class];

      if (from)
        changed = this.selectItem('firstDetectionDate', from) || changed;

      if (to)
        changed = this.selectItem('fixDate', to) || changed;

      return changed;
    },

    deselectByState : function (state) {
      var that = this;

      var filterState = this.getState();

      if (!state[this._fromDate.class] && filterState[this._fromDate.class]) {
        this._fromDate.set('value', null , false);
        this._fromTime.set('value', null, false);
      }

      if (!state[this._toDate.class] && filterState[this._toDate.class]) {
        this._toDate.set('value', null , false);
        this._toTime.set('value', null, false);
      }
    },

    stateDecoder : function (str) {
      return new Date(str);
    },

    getUrlState : function () {
      var state = {};

      var from = this._fromDate.get('displayedValue');
      var fromTime = this._fromTime.get('displayedValue');

      var to = this._toDate.get('displayedValue');
      var toTime = this._toTime.get('displayedValue')

      if (from)
        state[this._fromDate.class] = from + ' ' + fromTime;

      if (to)
        state[this._toDate.class] = to + ' ' + toTime;

      return state;
    },

    getState : function () {
      var urlState = this.getUrlState();

      var state = {};
      var from = new Date(urlState[this._fromDate.class]);
      var to   = new Date(urlState[this._toDate.class]);

      if (!isNaN(from))
        state[this._fromDate.class] = util.dateToUTCTime(from) / 1000;

      if (!isNaN(to))
        state[this._toDate.class] = util.dateToUTCTime(to) / 1000;

      return state;
    },

    clearAll : function () {
      this._fromDate.set('value', null, false);
      this._fromTime.set('value', null, false);

      this._toDate.set('value', null, false);
      this._toTime.set('value', null, false);
    }
  });

  var UniqueCheckBox = declare(FilterBase, {
    constructor : function () {
      var that = this;

      this._defaultValue = true; // Enabled by default.
      this._isUnique = this._defaultValue;

      this._uniqueCheckBox = new CheckBox({
        checked : this._defaultValue,
        onChange : function (changed) {
          that._isUnique = changed;

          topic.publish('filterchange', {
            parent : that.parent,
            changed : that.getUrlState()
          });
        }
      });

      this._uniqueCheckBoxLabel = dom.create('label', {
        for : this._uniqueCheckBox.get('id'),
        innerHTML : 'Unique reports'
      });
    },

    postCreate : function () {
      this.inherited(arguments);
      dom.empty(this.domNode);

      this.addChild(this._uniqueCheckBox);
      dom.place(this._uniqueCheckBoxLabel,
        this._uniqueCheckBox.domNode, 'after');
    },

    selectItem : function (key, value) {},

    setState : function (state) {
      var changed = false;

      var newState = state[this.class] === 'off' ? false : true;
      if (this._isUnique !== newState) {
        this._isUnique = newState;
        this._uniqueCheckBox.set('checked', this._isUnique, false);
        changed = true
      }

      return changed;
    },

    deselectByState : function (state) {
      this.setState(state);
      this._uniqueCheckBox.set('checked', this._isUnique);
    },

    getUrlState : function () {
      return {
        [this.class] : this._isUnique ? 'on' : 'off'
      };
    },

    getState : function () {
      return {
        [this.class] : this._isUnique
      };
    },

    clearAll : function () {
      this._isUnique = this._defaultValue;
      this._uniqueCheckBox.set('checked', this._isUnique, false);
    }
  });

  return declare(ContentPane, {
    constructor : function (args) {
      dojo.safeMixin(this, args);

      var that = this;

      this._filters = [];
      this._isUnique = true;

      this._topBarPane = dom.create('div', { class : 'top-bar'});

      //--- Clear all filter button ---//

      this._clearAllButton = new Button({
        class   : 'clear-all-btn',
        label   : 'Clear All Filters',
        onClick : function () {
          //--- Clear selected items ---//

          that.clearAll();

          //--- Remove states from the url ---//

          topic.publish('filterchange', {
            parent : that,
            changed : that.getUrlState()
          });
        }
      });

      this._uniqueReportsCheckBox = new UniqueCheckBox({
        class : 'is-unique',
        parent   : this,
        getItems : function () {
          var deferred = new Deferred();
          deferred.resolve([]);
          return deferred;
        }
      });
      this._filters.push(this._uniqueReportsCheckBox);

      this._reportCountWrapper = dom.create('span', {
        class : 'report-count-wrapper'
      }, this._topBarPane);

      this._reportCountIcon = dom.create('span', {
        class : 'customIcon bug'
      }, this._reportCountWrapper);

      this._reportCount = dom.create('span', {
        class : 'report-count',
        innerHTML : 0
      }, this._reportCountWrapper);

      //--- Normal or Diff view filters ---//

      if (this.baseline || this.newcheck || this.difftype) {
        this._runNameBaseFilter = new SelectFilter({
          class    : 'baseline',
          title    : 'Baseline',
          parent   : this,
          getSkippedValues : function () {
            return Object.keys(this.runNameNewCheckFilter._selectedFilterItems);
          },
          getItems : function () {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            CC_SERVICE.getRunReportCounts(null, reportFilter,
            function (res) {
              deferred.resolve(res.map(function (runReportCount) {
                return {
                  label : runReportCount.name,
                  value : runReportCount.runId,
                  count : runReportCount.reportCount
                };
              }));
            });

            return deferred;
          },
          enableSearch : true,
          filterLabel  : 'Search for run names...'
        });
        this._filters.push(this._runNameBaseFilter);

        this._runNameNewCheckFilter = new SelectFilter({
          class    : 'newcheck',
          title    : 'Newcheck',
          parent   : this,
          getSkippedValues : function () {
            return Object.keys(that._runNameBaseFilter._selectedFilterItems);
          },
          getItems : function () {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            CC_SERVICE.getRunReportCounts(null, reportFilter,
            function (res) {
              deferred.resolve(res.map(function (runReportCount) {
                return {
                  label : runReportCount.name,
                  value : runReportCount.runId,
                  count : runReportCount.reportCount
                };
              }));
            });

            return deferred;
          },
          enableSearch : true,
          filterLabel  : 'Search for run names...'
        });
        this._filters.push(this._runNameNewCheckFilter);

        this._runNameBaseFilter.set('runNameNewCheckFilter',
          this._runNameNewCheckFilter);

        this._diffTypeFilter = new SelectFilter({
          class    : 'difftype',
          title    : 'Diff type',
          parent   : this,
          defaultValues : function () {
            return { [this.class] : [CC_OBJECTS.DiffType.NEW] };
          },
          disableMultipleOption : true,

          getItems : function () {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            var runIds = reportFilter.baseline;

            var query = Object.keys(CC_OBJECTS.DiffType).map(function (key) {
              var d = new Deferred();

              var cmpData = null;
              if (reportFilter.newcheck) {
                cmpData = new CC_OBJECTS.CompareData();
                cmpData.runIds = reportFilter.newcheck;
                cmpData.diffType = CC_OBJECTS.DiffType[key];
              }

              CC_SERVICE.getRunResultCount(runIds, reportFilter, cmpData,
              function (res) {
                d.resolve({ [key] : res});
              });

              return d.promise;
            });

            all(query).then(function (res) {
              deferred.resolve(Object.keys(CC_OBJECTS.DiffType)
              .map(function (key, index) {
                var value = CC_OBJECTS.DiffType[key];

                var label;
                switch (key) {
                  case 'NEW':
                    label = 'Only in Newcheck (New)';
                    break;

                  case 'RESOLVED':
                    label = 'Only in Baseline (Resolved)';
                    break;

                  case 'UNRESOLVED':
                    label = 'Both in Baseline and Newcheck (Unresolved)';
                    break;
                }

                return {
                  label : label,
                  value : value,
                  count : res[index][key]
                };
              }));
            });

            return deferred;
          }
        });
        this._filters.push(this._diffTypeFilter);
      } else {
        this._runNameFilter = new SelectFilter({
          class    : 'run',
          title    : 'Run name',
          parent   : this,
          getItems : function () {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            CC_SERVICE.getRunReportCounts(null, reportFilter,
            function (res) {
              deferred.resolve(res.map(function (runReportCount) {
                return {
                  label : runReportCount.name,
                  value : runReportCount.runId,
                  count : runReportCount.reportCount
                };
              }));
            });

            return deferred;
          },
          enableSearch : true,
          filterLabel  : 'Search for run names...'
        });
        this._filters.push(this._runNameFilter);
      }

      //--- Review status filter ---//

      this._reviewStatusFilter = new SelectFilter({
        class : 'review-status',
        title : 'Review status',
        parent   : this,
        stateConverter : function (value) {
          return util.enumValueToKey(
            CC_OBJECTS.ReviewStatus, value).toLowerCase();
        },
        stateDecoder : function (key) {
          return CC_OBJECTS.ReviewStatus[key.toUpperCase()];
        },
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getReviewStatusCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(CC_OBJECTS.ReviewStatus).map(
              function (key) {
                var value = CC_OBJECTS.ReviewStatus[key];
                return {
                  label     : util.reviewStatusFromCodeToString(value),
                  value     : value,
                  count     : res[value] !== undefined ? res[value] : 0,
                  iconClass : 'customIcon ' + util.reviewStatusCssClass(value)
                };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._reviewStatusFilter);

      //--- Detection status filter ---//

      this._detectionStatusFilter = new SelectFilter({
        class : 'detection-status',
        title : 'Detection status',
        parent   : this,
        stateConverter : function (value) {
          return util.enumValueToKey(
            CC_OBJECTS.DetectionStatus, value).toLowerCase();
        },
        stateDecoder : function (key) {
          return CC_OBJECTS.DetectionStatus[key.toUpperCase()];
        },
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getDetectionStatusCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(CC_OBJECTS.DetectionStatus).map(
              function (key) {
                var value = CC_OBJECTS.DetectionStatus[key];
                return {
                  label     : util.detectionStatusFromCodeToString(value),
                  value     : value,
                  count     : res[value] !== undefined ? res[value] : 0,
                  iconClass : 'customIcon detection-status-' + key.toLowerCase()
                };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._detectionStatusFilter);

      //--- Severity filter ---//

      this._severityFilter = new SelectFilter({
        class : 'severity',
        title : 'Severity',
        parent   : this,
        stateConverter : function (value) {
          return util.enumValueToKey(CC_OBJECTS.Severity, value).toLowerCase()
        },
        stateDecoder : function (key) {
          return CC_OBJECTS.Severity[key.toUpperCase()];
        },
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getSeverityCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(CC_OBJECTS.Severity).sort(
              function (a, b) {
                return CC_OBJECTS.Severity[a] < CC_OBJECTS.Severity[b];
              }).map(function (key) {
                var value = CC_OBJECTS.Severity[key];
                return {
                  label     : key[0] + key.slice(1).toLowerCase(),
                  value     : value,
                  count     : res[value] !== undefined ? res[value] : 0,
                  iconClass : 'customIcon icon-severity-' + key.toLowerCase()
                };
              }));
          });

          return deferred;
        }
      });
      this._filters.push(this._severityFilter);

      //--- Run history tags filter ---//

      this._runHistoryTagFilter = new SelectFilter({
        class : 'run-history-tag',
        title : 'Run tag',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for run tags...',
        createItem : function (runHistoryTagCount) {
          return runHistoryTagCount.map(function (tag) {
            return {
              label : tag.name,
              value : tag.time,
              count : tag.count,
              iconClass : 'customIcon tag',
              iconStyle : 'color: ' + util.strToColor(tag.name)
            };
          });
        },
        stateConverter : function (value) {
          var item = this._items.filter(function (item) {
            return item.value === value;
          });

          return item.length ? item[0].label : null;
        },
        stateDecoder : function (key) {
          // If no item is available, get items from the server to decode URL
          // value.
          if (!this._items) {
            var runs = that.getRunIds();
            var reportFilter = that.getReportFilters();

            var res = CC_SERVICE.getRunHistoryTagCounts(
              runs.baseline, reportFilter, runs.newcheck);
            this._items = this.createItem(res);
          }

          var item = this._items.filter(function (item) {
            return item.label === key;
          });

          return item.length ? item[0].value : null;
        },
        getItems : function () {
          var self = this;
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getRunHistoryTagCounts(runs.baseline, reportFilter,
          runs.newcheck, function (res) {
            deferred.resolve(self.createItem(res));
          });

          return deferred;
        }
      });
      this._filters.push(this._runHistoryTagFilter);

      //--- Detection date filter ---//

      this._detectionDateFilter = new DateFilter({
        class    : 'detection-date',
        title    : 'Detection date',
        parent   : this,
        getItems : function () {
          var deferred = new Deferred();

          deferred.resolve([
            { label : 'Today', value : 'today', iconClass : 'customIcon text-icon today' },
            { label : 'Yesterday', value : 'yesterday', iconClass : 'customIcon text-icon yesterday' }
          ]);

          return deferred;
        }
      });
      this._filters.push(this._detectionDateFilter);

      //--- File path filter ---//

      this._fileFilter = new SelectFilter({
        class : 'filepath',
        title : 'File',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for files...',
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getFileCounts(runs.baseline, reportFilter, runs.newcheck,
          function (res) {
            deferred.resolve(Object.keys(res).sort(alphabetical)
            .map(function (file) {
              return {
                label : '&lrm;' + file,
                value : file,
                count : res[file]
              };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._fileFilter);

      //--- Checker name filter ---//

      this._checkerNameFilter = new SelectFilter({
        class : 'checker-name',
        title : 'Checker name',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for checker names...',
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getCheckerCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(res.sort(function (a, b) {
              if (a.name < b.name) return -1;
              if (a.name > b.name) return 1;

              return 0;
            }).map(function (checker) {
              return {
                label : checker.name,
                value : checker.name,
                count : checker.count
              };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._checkerNameFilter);

      //--- Checker message filter ---//

      this._checkerMessageFilter = new SelectFilter({
        class : 'checker-msg',
        title : 'Checker message',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for checker messages...',
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getCheckerMsgCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(res).sort(alphabetical)
            .map(function (msg) {
              return {
                label : msg,
                value : msg,
                count : res[msg]
              };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._checkerMessageFilter);

      this._clearAllButton.set('filters', this._filters);

      //--- Select items from the current url state ---//

      var state = hashHelper.getState();

      if (this.runData || this.diffView || state.tab === 'allReports') {
        if (this.runData && !state.run)
          state.run = this.runData.runId;
        else if ((this.baseline && !state.baseline) ||
          (this.newcheck && !state.newcheck)) {
          if (this.baseline)
            state.baseline = this.baseline.runId;
          if (this.newcheck)
            state.newcheck = this.newcheck.runId;
          state.difftype = this.difftype || CC_OBJECTS.DiffType.NEW;
        }
      } else {
        //--- All report tab case ---//

        if (state.report === undefined && state.reportHash === undefined) {
          state = {};
        } else {
          hashHelper.setStateValue('tab', 'allReports');
          topic.publish('tab/allReports');
        }
      }

      this.refreshFilters(state, true);

      this._subscribeTopics();
    },

    clearAll : function () {
      var state = this.getState();
      Object.keys(state).forEach(function (key) {
        state[key] = null;
      });

      this._filters.forEach(function (filter) {
        filter.clearAll();
      });

      return state;
    },

    /**
     * Returns run informations for normal and diff view.
     * @property baseline In normal view it will contain the run ids. Otherwise
     * it will contain information of the base filter.
     * @property newcheck In normal view it will null. Otherwise it will contain
     * information of thrift CompareData informations.
     */
    getRunIds : function () {
      if (this.diffView) {
        var diffType = this._diffTypeFilter.getState()[this._diffTypeFilter.class];
        var newCheckIds =
          this._runNameNewCheckFilter.getState()[this._runNameNewCheckFilter.class];

        var cmpData = null;
        if (newCheckIds) {
          var cmpData = new CC_OBJECTS.CompareData();
          cmpData.runIds = newCheckIds;
          cmpData.diffType = diffType ? diffType[0] : CC_OBJECTS.DiffType.NEW;
        }

        return {
          baseline : this._runNameBaseFilter.getState()[this._runNameBaseFilter.class],
          newcheck : cmpData
        };
      } else {
        return {
          baseline : this._runNameFilter.getState()[this._runNameFilter.class],
          newcheck : null
        };
      }
    },

    postCreate : function () {
      var that = this;

      dom.place(this._clearAllButton.domNode, this._topBarPane);
      dom.place(this._uniqueReportsCheckBox.domNode, this._topBarPane)
      dom.place(this._topBarPane, this.domNode);

      this._filters.forEach(function (filter) {
        if (that._uniqueReportsCheckBox.class !== filter.class)
          that.addChild(filter);
      });
    },

    /**
     * Return the current state of the filters as an object.
     */
    getState : function () {
      var state = {};

      this._filters.forEach(function (filter) {
        Object.assign(state, filter.getState());
      });

      return state;
    },

    /**
     * Return the current URL state of the filters as an object.
     */
    getUrlState : function () {
      var state = {};

      this._filters.forEach(function (filter) {
        Object.assign(state, filter.getUrlState());

        //--- Load default values for the first time ---//

        if (!filter.initalized && filter.defaultValues) {
          var defaultValues = filter.defaultValues();
          for (var key in defaultValues) {
            if (state[key] === null)
              state[key] = defaultValues[key];
          }
          filter.initalized = true;
        }
      });

      return state;
    },

    /**
     * Returns CamelCased version of the parameter.
     */
    getReportFilterName : function (key) {
      return key.split('-').map(function (str, ind) {
        if (ind === 0)
          return str;

        return str.charAt(0).toUpperCase() + str.slice(1);
      }).join('');
    },

    /**
     * Creates report filters for the selected filter.
     */
    getReportFilters : function () {
      var that = this;

      var reportFilter = new CC_OBJECTS.ReportFilter();
      reportFilter.isUnique = this._isUnique;

      this._filters.forEach(function (filter) {
        var state = filter.getState();
        Object.keys(state).forEach(function (key) {
          var reportFilterName = that.getReportFilterName(key);
          reportFilter[reportFilterName] = state[key];
        });
      });

      return reportFilter;
    },

    /**
     * Deselecting items which are not active by the URL state.
     */
    deselectByState : function (state) {
      this._filters.forEach(function (filter) {
        filter.deselectByState(state);
      });
    },

    /**
     * Select filter items from the current url state.
     */
    refreshFilters : function (state, force) {
      var that = this;

      var changed = false || force;
      this._filters.forEach(function (filter) {
        changed = filter.setState(state) || changed;
      });

      if (!changed)
        return;

      var finished = 0;
      this._filters.forEach(function (filter) {
        filter.loading();

        filter.getItems().then(function (items) {
          filter._items = items;

          filter.setState(state);
          var filterState = filter.getState();

          Object.keys(filterState).forEach(function (key) {
            if (filterState[key]) {
              if (!Array.isArray(filterState[key]))
                filterState[key] = [filterState[key]];

              filterState[key].forEach(function (item) {
                filter.selectItem(key, item, true);
              });
            }
          });

          filter.loaded();
          ++finished;

          //--- Update title if all children are loaded and selected ---//

          if (finished === that._filters.length)
            that._updateTitle();
        });
      });

      var runs = that.getRunIds();
      var reportFilter = this.getReportFilters();

      CC_SERVICE.getRunResultCount(runs.baseline, reportFilter,
      runs.newcheck, function (count) {
        that._reportCount.innerHTML = count;
      });
    },

    /**
     * Subscribe on topics.
     */
    _subscribeTopics : function () {
      var that = this;

      // When "browser back" or "browser forward" button is pressed we update
      // the filter by the url state.
      that._hashChangeTopic = topic.subscribe('/dojo/hashchange',
      function (url) {
        if (!that.hashChangeInProgress && that.parent.selected) {
          var state = hashHelper.getState();
          that.deselectByState(state);
          that.refreshFilters(state);
        }

        that.hashChangeInProgress = false;
      });

      // When any filter is changed, we have to update all the filters.
      that._filterChangeTopic = topic.subscribe('filterchange',
      function (state) {
        if (that.parent.selected) {
          that.hashChangeInProgress = true;
          that.refreshFilters(state.changed, true);
          hashHelper.setStateValues(state.changed);
        }
      });
    },

    _updateTitle : function () {
      if (this.runData) {
        var items = this._runNameFilter.getSelectedItem();

        if (!items.length)
          this.parent.set('title', 'All reports');
        else if (items.length === 1)
          this.parent.set('title', items[0] ? items[0].label : 'Unknown run');
        else
          this.parent.set('title', 'Multiple runs');
      } else if (this.baseline || this.newchek) {
        var baseline = this._runNameBaseFilter.getSelectedItem();
        var newcheck = this._runNameNewCheckFilter.getSelectedItem();

        if (baseline.length === 1 || newcheck.length === 1)
          this.parent.set('title', 'Diff of '
            + (baseline[0] ? baseline[0].label : 'Unknown run') + ' and '
            + (newcheck[0] ? newcheck[0].label : 'Unknown run'));
        else {
          this.parent.set('title', 'Diff of multiple runs');
        }
      }
    },

    destroy : function () {
      this.inherited(arguments);

      this._hashChangeTopic.remove();
      this._filterChangeTopic.remove();
    }
  });
});
