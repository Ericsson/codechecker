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
  'dijit/form/TextBox',
  'dijit/popup',
  'dijit/TooltipDialog',
  'dijit/layout/ContentPane',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, Deferred, dom, domClass, all, topic, Standby, Button,
  TextBox, popup, TooltipDialog, ContentPane, hashHelper, util) {

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
          class : this.iconClass
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

      if (this.search.enable)
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
      if (this.search.enable)
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
             ? '<span class="' + item.iconClass + '"></span>'
             : '')
          + '<span class="label">' + item.label + '</span>'
          + '<span class="count">' + item.count + '</span>';

        var selected = item.value in that.reportFilter._selectedFilterItems;

        var disabled = skippedList.indexOf(item.value.toString()) !== -1;

        if (disabled)
          return;

        dom.create('div', {
          class     : 'select-menu-item ' + (selected ? 'selected' : ''),
          innerHTML : content,
          onclick   : function () {
            if (that.disableMultipleOption) {
              that.reportFilter.clearAll();
              that.reportFilter.selectItem(item.value);
              that._render();
              return;
            }

            if (item.value in that.reportFilter._selectedFilterItems) {
              that.reportFilter.deselectItem(item.value);
              domClass.remove(this, 'selected');
            } else {
              that.reportFilter.selectItem(item.value);
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
  var FilterBase = declare(ContentPane, {

    constructor : function (args) {
      dojo.safeMixin(this, args);

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
      })
    },

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
              changed : {[that.class] : that.getState()}
            });
          }
        }, this._options);

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

      //--- Loading widget ---//

      this._standBy = new Standby({
        target : this.domNode,
        color : '#ffffff'
      });
      this.addChild(this._standBy);
    },

    /**
     * Return the current state of the filter as an array. If no filter item is
     * selected it returns null.
     */
    getState : function () {
      var state = Object.keys(this._selectedFilterItems).map(function (key) {
        return isNaN(key) ? key : parseInt(key);
      });

      return state.length ? state : null;
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
     * @param value {integer|string} - Value of the selected item.
     * @param preventFilterChange - If true it prevents the filter change event.
     */
    selectItem : function (value, preventFilterChange) {
      var that = this;

      var item = this.getItem(value);

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
          changed : {[this.class] : this.getState()}
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
          changed : {[this.class] : this.getState()}
        });
      }
    },

    /**
     * Clears all selected items.
     */
    clearAll : function () {
      for (key in this._selectedFilterItems) {
        var item = this._selectedFilterItems[key];

        if (item)
          this.deselectItem(item.value, true);
      }
    },

    loading : function () {
      this._standBy.show();
    },

    loaded : function () {
      this._standBy.hide();
    },

    destroy : function () {
      this.inherited(arguments);

      this._standBy.destroyRecursive();
    },

    getSkippedValues : function () { return []; }
  });

  return declare(ContentPane, {
    constructor : function (args) {
      dojo.safeMixin(this, args);

      var that = this;

      this._filters = [];

      //--- Cleare all filter button ---//

      this._clearAllButton = new Button({
        class   : 'clear-all-btn',
        label   : 'Clear All Filters',
        onClick : function () {
          //--- Clear selected items ---//

          this.filters.forEach(function (filter) {
            filter.clearAll();
          });

          //--- Remove states from the url ---//

          topic.publish('filterchange', {
            parent : that,
            changed : that.getState()
          });
        }
      });

      this._reportCountWrapper = dom.create('span', {
        class : 'report-count-wrapper'
      });

      this._reportCountIcon = dom.create('span', {
        class : 'customIcon bug'
      }, this._reportCountWrapper);

      this._reportCount = dom.create('span', {
        class : 'report-count',
        innerHTML : 0
      }, this._reportCountWrapper);

      //--- Normal or Diff view filters ---//

      if (this.baseline || this.newcheck || this.difftype) {
        this._runNameBaseFilter = new FilterBase({
          class    : 'baseline',
          reportFilterName : 'baseline',
          title    : 'Baseline',
          parent   : this,
          getSkippedValues : function () {
            return Object.keys(this.runNameNewCheckFilter._selectedFilterItems);
          },
          getItems : function (query) {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            CC_SERVICE.getRunReportCounts(null, reportFilter,
            function (res) {
              deferred.resolve(res.map(function (runReportCount) {
                return {
                  label : runReportCount.name,
                  value : runReportCount.runId,
                  count : runReportCount.reportCount,
                };
              }));
            });

            return deferred;
          },
          enableSearch : true,
          filterLabel  : 'Search for run names...'
        });
        this._filters.push(this._runNameBaseFilter);

        this._runNameNewCheckFilter = new FilterBase({
          class    : 'newcheck',
          reportFilterName : 'newcheck',
          title    : 'Newcheck',
          parent   : this,
          getSkippedValues : function () {
            return Object.keys(that._runNameBaseFilter._selectedFilterItems);
          },
          getItems : function (query) {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            CC_SERVICE.getRunReportCounts(null, reportFilter,
            function (res) {
              deferred.resolve(res.map(function (runReportCount) {
                return {
                  label : runReportCount.name,
                  value : runReportCount.runId,
                  count : runReportCount.reportCount,
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

        this._diffTypeFilter = new FilterBase({
          class    : 'difftype',
          reportFilterName : 'difftype',
          title    : 'Diff type',
          parent   : this,
          defaultValues : [CC_OBJECTS.DiffType.NEW],
          disableMultipleOption : true,
          getItems : function (query) {
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
                return {
                  label     : key.charAt(0) + key.slice(1).toLowerCase(),
                  value     : value,
                  count     : res[index][key]
                };
              }));
            });

            return deferred;
          }
        });
        this._filters.push(this._diffTypeFilter);
      } else {
        this._runNameFilter = new FilterBase({
          class    : 'run',
          reportFilterName : 'run',
          title    : 'Run name',
          parent   : this,
          getItems : function (query) {
            var deferred = new Deferred();

            var reportFilter = that.getReportFilters();
            CC_SERVICE.getRunReportCounts(null, reportFilter,
            function (res) {
              deferred.resolve(res.map(function (runReportCount) {
                return {
                  label : runReportCount.name,
                  value : runReportCount.runId,
                  count : runReportCount.reportCount,
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

      this._reviewStatusFilter = new FilterBase({
        class : 'review-status',
        reportFilterName : 'reviewStatus',
        title : 'Review status',
        parent   : this,
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getReviewStatusCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(ReviewStatus).map(function (key) {
              var value = ReviewStatus[key];
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

      this._detectionStatusFilter = new FilterBase({
        class : 'detection-status',
        reportFilterName : 'detectionStatus',
        title : 'Detection status',
        parent   : this,
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getDetectionStatusCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(DetectionStatus).map(function (key) {
              var value = DetectionStatus[key];
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

      this._severityFilter = new FilterBase({
        class : 'severity',
        reportFilterName : 'severity',
        title : 'Severity',
        parent   : this,
        getItems : function () {
          var deferred = new Deferred();

          var runs = that.getRunIds();
          var reportFilter = that.getReportFilters();

          CC_SERVICE.getSeverityCounts(runs.baseline, reportFilter,
            runs.newcheck, function (res) {
            deferred.resolve(Object.keys(Severity).sort(function (a, b) {
              return Severity[a] < Severity[b];
              }).map(function (key) {
                var value = Severity[key];
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

      //--- File path filter ---//

      this._fileFilter = new FilterBase({
        class : 'file',
        reportFilterName : 'filepath',
        title : 'File',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for files...',
        getItems : function (query) {
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
                count : res[file],
              };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._fileFilter);

      //--- Checker name filter ---//

      this._checkerNameFilter = new FilterBase({
        class : 'checker',
        reportFilterName : 'checkerName',
        title : 'Checker name',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for checker names...',
        getItems : function (query) {
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
                count : checker.count,
              };
            }));
          });

          return deferred;
        }
      });
      this._filters.push(this._checkerNameFilter);

      //--- Checker message filter ---//

      this._checkerMessageFilter = new FilterBase({
        class : 'checker-msg',
        reportFilterName : 'checkerMsg',
        title : 'Checker message',
        parent   : this,
        enableSearch : true,
        filterLabel : 'Search for checker messages...',
        getItems : function (query) {
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
                count : res[msg],
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

      if (this.runData || this.diffView || state.allReports) {
        if (this.runData && !state.run)
          state.run = this.runData.runId;
        else if ((this.baseline && !state.baseline) ||
          (this.newcheck && !state.newcheck)) {
          if (this.baseline)
            state.baseline = this.baseline.runId;
          if (this.newcheck)
            state.newcheck = this.newcheck.runId;
        }
      } else {
        //--- All report tab case ---//

        if (state.report === undefined)
          state = {};
        else
          hashHelper.setStateValue('allReports', true);
      }

      this.refreshFilters(state, true);

      this._subscribeTopics();
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
        var diffType = this._diffTypeFilter.getState();
        var newCheckIds = this._runNameNewCheckFilter.getState();

        var cmpData = null;
        if (newCheckIds) {
          var cmpData = new CC_OBJECTS.CompareData();
          cmpData.runIds = newCheckIds;
          cmpData.diffType = diffType ? diffType[0] : CC_OBJECTS.DiffType.NEW;
        }

        return {
          baseline : this._runNameBaseFilter.getState(),
          newcheck : cmpData
        };
      } else {
        return {
          baseline : this._runNameFilter.getState(),
          newcheck : null
        };
      }
    },

    postCreate : function () {
      var that = this;

      this.addChild(this._clearAllButton);
      dom.place(this._reportCountWrapper, this.domNode);

      this._filters.forEach(function (filter) {
        that.addChild(filter);
      });
    },

    /**
     * Return the current state of the filters as an object.
     */
    getState : function () {
      var state = {};

      this._filters.forEach(function (filter) {
        state[filter.class] = filter.getState();
      });

      return state;
    },

    /**
     * Creates report filters for the selected filter.
     */
    getReportFilters : function () {
      var reportFilter = new CC_OBJECTS.ReportFilter();

      this._filters.forEach(function (filter) {
        var state = filter.getState();
        if (state)
          reportFilter[filter.reportFilterName] = state;
      });

      return reportFilter;
    },

    /**
     * Select filter items from the current url state.
     */
    refreshFilters : function (state, force) {
      var that = this;

      var changed = false || force;
      this._filters.forEach(function (filter) {
        var filterState = state[filter.class] ? state[filter.class] : [];
        if (!(filterState instanceof Array))
          filterState = [filterState];

        filterState.forEach(function (value) {
          if (!filter._selectedFilterItems[value]) {
            filter._selectedFilterItems[value] = null;
            changed = true;
          }
        });
      });

      if (!changed)
        return;

      var finished = 0;
      this._filters.forEach(function (filter) {
        filter.loading();
        var filterState = filter.getState();

        filter.getItems().then(function (items) {
          filter._items = items;

          if (filterState)
            filterState.forEach(function (item) {
              filter.selectItem(item, true);
            });

          //--- Load default values for the first time ---//

          if (!filter.initalized && filter.defaultValues
            && !filter.getState()) {
            filter.defaultValues.forEach(function (value) {
              filter.selectItem(value, true);
            });
            filter.initalized = true;
          }

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
        if (!that.hashChangeInProgress && that.parent.selected)
          that.refreshFilters(hashHelper.getState());

        that.hashChangeInProgress = false;
      });

      // When any filter is changed, we have to update all the filters.
      that._filterChangeTopic = topic.subscribe('filterchange',
      function (state) {
        if (that.parent.selected) {
          that.hashChangeInProgress = true;
          that.refreshFilters(that.getState(), true);
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
