// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojox/widget/Standby',
  'dijit/layout/ContentPane',
  'codechecker/filter/FilterBase',
  'codechecker/filter/FilterTooltip',
  'codechecker/filter/SelectedFilterItem'],
function (declare, dom, Standby, ContentPane, FilterBase, FilterTooltip,
  SelectedFilterItem) {
  return declare([FilterBase, ContentPane], {
    constructor : function () {
      this.selectedItems = {}; // Selected filter items.
    },

    postCreate : function () {
      this.initHeader();

      //--- Selected filter items ---//

      this._selectedFilterItems = new ContentPane({ class : 'items' });
      this.addChild(this._selectedFilterItems);

      this._noFilterItem = new SelectedFilterItem({
        class : 'select-menu-item none',
        label : 'No filter',
        options : { disableCount : true, disableRemove : true }
      });
      this._selectedFilterItems.addChild(this._noFilterItem);

      this._standBy = new Standby({
        target : this.domNode,
        color : '#ffffff'
      });
      this.addChild(this._standBy);
    },

    // Initalize filter header with a clear and list available option ability.
    initHeader : function () {
      var that = this;

      //--- Filter header ---//

      this._header = dom.create('div', { class : 'header' }, this.domNode);

      this._title = dom.create('span', {
        class     : 'title',
        innerHTML : this.title
      }, this._header);

      this._options = dom.create('span', { class : 'options' }, this._header);

      //--- Clear filter ---//

      this._clean = dom.create('span', {
        class : 'customIcon clean',
        onclick : function () {
          that.clear();
          that.notifyOthers();
        }
      }, this._options);

      //--- Filter options ---//

      this._edit = dom.create('span', {
        class : 'customIcon cogwheel',
        onclick : function () {
          that._filterTooltip.show();
        }
      }, this._options);

      this._filterTooltip = new FilterTooltip({
        class : this.class,
        around : this._edit,
        search : this.search,
        reportFilter : this
      });
    },

    // Get available filter items.
    getItems : function () {},

    // Get icon class for filter items.
    getIconClass : function (value) {},

    // Decodes the parameter. This function will be used when we set the report
    // filters.
    stateDecoder : function (key) { return key; },

    // Update report filter by the state parameter.
    updateReportFilter : function (state) {},

    // Returns the URL state of this filter.
    getUrlState : function () {
      var state = {};

      var keys = Object.keys(this.selectedItems);
      state[this.class] = keys.length ? keys : null;

      return state;
    },

    // Returns the selected filter item values.
    getSelectedItemValues : function () {
      var keys = Object.keys(this.selectedItems);
      if (!keys.length) return null;

      var that = this;
      return keys.map(function (value) { return that.stateDecoder(value); });
    },

    // Initalize filter state by query parameters.
    initByUrl : function (queryParams) {
      var that = this;
      var state = queryParams[this.class];

      if (!state)
        state = [];

      if (!(state instanceof Array))
        state = [state];

      // Deselect items which are selected and not in query params.
      for (var key in this.selectedItems)
        if (state.indexOf(key) === -1)
          this.deselect(key);

      // Select states by URL query parameters.
      state.forEach(function (value) { that.select(value); });

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    // Returns true if filter item identified by the parameter is selected.
    isSelected : function (value) {
      return this.selectedItems[value];
    },

    // Selects a filter item. If the item has already been selected, we update
    // the item by the options parameter.
    select : function (value, options) {
      var that = this;

      // Remove NO filter item if nothing is selected previously.
      if (!Object.keys(this.selectedItems).length)
        this._selectedFilterItems.getChildren().forEach(function (child) {
          that._selectedFilterItems.removeChild(child);
        });

      // If value is selected, update the options, otherwise create a new item.
      if (this.selectedItems[value]) {
        this.selectedItems[value].update(options);
      } else {
        var label = value;
        if (this.labelFormatter)
          label = this.labelFormatter(label);

        this.selectedItems[value] = new SelectedFilterItem({
          class : 'select-menu-item',
          label : label,
          iconClass : that.getIconClass(value),
          iconStyle : that.getIconStyle ? that.getIconStyle(value) : null,
          options : options,
          onClick : function () {
            that.deselect(value);
            that.notifyOthers();
            this.destroy();
          }
        });
        this._selectedFilterItems.addChild(this.selectedItems[value]);
      }

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    // Deselects a filter item.
    deselect : function (value) {
      var item = this.selectedItems[value];
      if (!item) return;

      this._filterTooltip.deselect(value);
      this._selectedFilterItems.removeChild(item);
      delete this.selectedItems[value];

      if (!Object.keys(this.selectedItems).length)
        this._selectedFilterItems.addChild(this._noFilterItem);

      var state = this.getSelectedItemValues();
      this.updateReportFilter(state);
    },

    // Clears out the filter state.
    clear : function () {
      for (var key in this.selectedItems)
        this._selectedFilterItems.removeChild(this.selectedItems[key]);

      this._selectedFilterItems.addChild(this._noFilterItem);
      this.selectedItems = {};
      this._filterTooltip.reset();
      this.updateReportFilter(null);
    },

    // Notify other filters on filter change.
    notifyOthers : function () {
      this.parent.notifyAll([this]);
    },

    // Subscribe on notification events.
    notify : function () {
      this._filterTooltip.reset();

      var selectedItems = Object.keys(this.selectedItems);
      var selectedItemLen = selectedItems.length;
      if (!selectedItemLen) return;

      var that = this;
      var opt = { filter : selectedItems };
      this._standBy.show();
      this.getItems(opt).then(function (items) {
        that._filterTooltip.reset(items);

        selectedItems.forEach(function (value) {
          var selectedServerItems = items.filter(function (item) {
            return value.toLowerCase() === item.value.toLowerCase();
          });
          that.select(value, selectedServerItems[0]);
          that._standBy.hide();
        });
      });
    },

    // Destroy DOM elements.
    destroy : function () {
      this.inherited(arguments);

      if (this._standBy)
        this._standBy.destroyRecursive();
    },
  });
});
