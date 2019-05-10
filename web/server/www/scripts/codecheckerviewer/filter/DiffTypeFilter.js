// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'dojo/dom-construct',
  'dojo/promise/all',
  'dojox/widget/Standby',
  'dijit/layout/ContentPane',
  'codechecker/filter/SelectFilter',
  'codechecker/filter/SelectedFilterItem',
  'codechecker/util'],
function (declare, Deferred, dom, all, Standby, ContentPane, SelectFilter,
  SelectedFilterItem, util) {

  return declare(SelectFilter, {
    constructor : function () {
      this.defaultDiffType = CC_OBJECTS.DiffType.NEW;
      this.currentDiffType = this.defaultDiffType;
      this.selectedItem = null;
    },

    postCreate : function () {
      this.initHeader();

      //--- Selected filter items ---//

      this._selectedFilterItems = new ContentPane({ class : 'items' });
      this.addChild(this._selectedFilterItems);

      this._standBy = new Standby({
        target : this.domNode,
        color : '#ffffff'
      });
      this.addChild(this._standBy);
    },

    labelFormatter : function (label) {
      switch (label) {
        case this.stateEncoder(CC_OBJECTS.DiffType.NEW):
          return 'Only in Newcheck';
        case this.stateEncoder(CC_OBJECTS.DiffType.RESOLVED):
          return 'Only in Baseline';
        case this.stateEncoder(CC_OBJECTS.DiffType.UNRESOLVED):
          return 'Both in Baseline and Newcheck';
        default:
          return 'Unknown';
      }
    },

    getItems : function (opt) {
      var deferred = new Deferred();

      var that = this;
      opt = this.parent.initReportFilterOptions(opt);

      if (!opt.cmpData)
        return deferred.resolve([]);

      // Get report filter count for each diff type.
      var query = Object.keys(CC_OBJECTS.DiffType).map(function (key) {
        opt.cmpData.diffType = CC_OBJECTS.DiffType[key];

        var d = new Deferred();
        CC_SERVICE.getRunResultCount(opt.runIds, opt.reportFilter, opt.cmpData,
        function (res) {
          var state = {};
          state[key] = res;
          d.resolve(state);
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
        return d.promise;
      });

      all(query).then(function (res) {
        deferred.resolve(Object.keys(CC_OBJECTS.DiffType)
        .map(function (key, index) {
          var value = CC_OBJECTS.DiffType[key];

          return {
            id    : value,
            value : that.stateEncoder(value),
            count : res[index][key]
          };
        }));
      });
      return deferred;
    },

    stateEncoder : function (value) {
      return util.diffTypeFromCodeToString(value).toLowerCase();
    },

    stateDecoder : function (key) {
      return CC_OBJECTS.DiffType[key.replace(' ', '_').toUpperCase()];
    },

    getUrlState : function () {
      var state = {};
      state[this.class] = this.currentDiffType === this.defaultDiffType
        ? null
        : this.stateEncoder(this.currentDiffType);
      return state;
    },

    initByUrl : function (queryParams) {
      var value = queryParams[this.class];

      // If multiple values can be found in the URL, get the first one.
      if (value instanceof Array)
        value = value[0];

      // If no diff type is provided in the URL, use the default diff type.
      if (!value)
        value = this.stateEncoder(this.defaultDiffType);

      this.select(value);
    },

    // Returns True if the the current selected item is the item which is given
    // in the parameter. Otherwise it returns False.
    isSelected : function (value) {
      return value === this.stateEncoder(this.currentDiffType);
    },

    select : function (value, options) {
      var that = this;
      this._selectedFilterItems.getChildren().forEach(function (child) {
        that._selectedFilterItems.removeChild(child);
      });

      var prevValue = this.stateEncoder(this.currentDiffType);
      this._filterTooltip.deselect(prevValue);

      this.currentDiffType = this.stateDecoder(value);

      var label = this.stateEncoder(this.currentDiffType);
      if (this.labelFormatter)
        label = this.labelFormatter(label);

      this.selectedItem = new SelectedFilterItem({
        class : 'select-menu-item',
        label : label,
        iconClass : that.getIconClass(value),
        options : options
      });
      this._selectedFilterItems.addChild(this.selectedItem);
      this.updateReportFilter(this.currentDiffType);
    },

    clear : function (defaultDiffType) {
      if (!defaultDiffType) defaultDiffType = this.defaultDiffType;

      for (var key in this.selectedItems)
        this._selectedFilterItems.removeChild(this.selectedItems[key]);

      this.currentDiffType = defaultDiffType;
      this.select(this.stateEncoder(this.currentDiffType));
      this._filterTooltip.reset();
      this.updateReportFilter(this.currentDiffType);
    },

    notify : function () {
      this._filterTooltip.reset();

      var that = this;
      this._standBy.show();
      this.getItems().then(function (items) {
        that._filterTooltip.reset(items);

        var selectedItems = items.filter(function (item) {
          return that.currentDiffType === item.id;
        });
        if (selectedItems.length)
          that.select(selectedItems[0].value, selectedItems[0]);
        that._standBy.hide();
      });
    }
  });
});
