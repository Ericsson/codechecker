// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/data/ItemFileWriteStore',
  'dojox/grid/DataGrid',
  'dijit/form/Button',
  'dijit/Dialog',
  'dijit/layout/ContentPane',
  'dijit/form/ValidationTextBox',
  'dijit/Tooltip',
  'codechecker/util'],
function (declare, dom, ItemFileWriteStore, DataGrid, Button, Dialog,
  ContentPane, ValidationTextBox, Tooltip, util) {

  var SaveFilterDialog = declare(Dialog, {
    save : function () {
      if (this.filterName.isValid()) {
        var that = this;

        var filterName = this.filterName.get('value');
        var filterValues = this.filterView.getUrlState();

        // Remove empty fields.
        Object.keys(filterValues).forEach(function (key) {
          if (filterValues[key] === null) {
            delete filterValues[key];
          }
        });

        CC_SERVICE.addReportFilter(filterName, JSON.stringify(filterValues),
        function (res) {
          if (res) {
            that.hide();
          }
        }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      }
    },

    postCreate : function () {
      this.inherited(arguments);

      var that = this;

      var contentArea = dom.create('div', {
        class: 'dijitDialogPaneContentArea'
      }, this.containerNode);

      this.filterName = new ValidationTextBox({
        class       : 'form-input',
        name        : 'filterName',
        placeholder : 'Filter name...',
        required    : true
      }).placeAt(contentArea);

      var actionBar = dom.create('div', {
        class: 'dijitDialogPaneActionBar'
      }, this.containerNode);

      new Button({
        label: 'Save',
        onClick: function() {
          that.save();
        }
      }).placeAt(actionBar);

      new Button({
        label: 'Cancel',
        onClick: function() {
          that.hide();
        }
      }).placeAt(actionBar);
    },

    onShow : function () {
      this.filterName.reset();
    }
  });

  function removeBtnFormatter(listOfFilters) {
    return function (filterId) {
      return new Button({
        label: 'Remove',
        iconClass : 'customIcon delete',
        onClick : function () {
          CC_SERVICE.removeReportFilter(filterId, function (res) {
            if (res) {
              listOfFilters.populateFilters();
            }
          }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
        }
      });
    };
  }

  var ListOfFilters = declare(DataGrid, {
    constructor : function () {
      this.createNewStore();

      this.structure = [
        { name : 'Name', field : 'name', cellClasses : 'link', width : '100%'},
        { name : '&nbsp;', field : 'remove', width : '100px', formatter : removeBtnFormatter(this) }
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;
      this.autoHeight = true;
    },

    createNewStore : function () {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });
    },

    clearGrid: function () {
      this.createNewStore();
      this.setStore(this.store);
    },

    addFilter : function (filter) {
      this.store.newItem({
        id : filter.id,
        name : filter.name,
        value : filter.value,
        remove : filter.id
      });
    },

    populateFilters : function () {
      this.clearGrid();

      var that = this;
      CC_SERVICE.getReportFilters(null, function (filters) {
        filters.forEach(function (filter) {
          that.addFilter(filter);
        });
      });
    },

    onCellMouseOver : function (evt) {
      if (evt.cell.field === 'name') {
        var that = this;

        var node = this.getRowNode(evt.rowIndex);
        var item = this.getItem(evt.rowIndex);

        var content = dom.create('div');

        var values = JSON.parse(item.value[0]);
        Object.keys(values).forEach(function (key) {
          var filter = that.filterView.getFilter(key);
          var title = filter && filter.title ? filter.title : key;

          var value = values[key];
          if (value instanceof Array) {
            if (filter) {
              value = value.map(function (element) {
                var icon = filter.getIconClass(element);
                return icon
                  ? element + ' (<i class="' + icon + '"></i>)'
                  : element;
              });
            }
            value = value.join(', ');
          }

          dom.create('div', {
            innerHTML : '<b>' + title + '</b>' + ': ' + value
          }, content);
        });

        Tooltip.show(content.outerHTML, node, ['above']);
      }
    },

    onCellMouseOut : function (evt) {
      if (evt.cell.field === 'name') {
        var node = this.getRowNode(evt.rowIndex);
        Tooltip.hide(node);
      }
    }
  });

  var LoadFilterDialog = declare(Dialog, {
    postCreate : function () {
      this.inherited(arguments);

      var that = this;

      var contentArea = dom.create('div', {
        class: 'dijitDialogPaneContentArea'
      }, this.containerNode);

      this._listOfFilters = new ListOfFilters({
        style : 'width: 400px;',
        filterView : this.filterView,
        onRowClick : function (evt) {
          var item = this.getItem(evt.rowIndex);

          if (evt.cell && evt.cell.field === 'name') {
            var values = JSON.parse(item.value[0]);
            that.filterView.initAll(values);
            that.hide();
          }
        }
      }).placeAt(contentArea);

      var actionBar = dom.create('div', {
        class: 'dijitDialogPaneActionBar'
      }, this.containerNode);

      new Button({
        label: 'Cancel',
        onClick: function() {
          that.hide();
        }
      }).placeAt(actionBar);
    },

    onShow : function () {
      this._listOfFilters.populateFilters();
    }
  });

  return declare(ContentPane, {
    postCreate : function () {
      var that = this;

      this._topBarPane = dom.create('div', { class : 'top-bar'}, this.domNode);
      var header = dom.create('div', {
        class : 'header'
      });
      this._title = dom.create('span', {
        class     : 'title',
        innerHTML : 'Manage Filters'
      }, header);

      dom.place(header, this._topBarPane);

      this._clearAllButton = new Button({
        class   : 'clear-all-btn filter-btn',
        label   : 'Clear All',
        onClick : function () {
          that.filterView.clearAll();
          that.filterView.notifyAll();
        }
      });
      dom.place(this._clearAllButton.domNode, this._topBarPane);

      this._saveFilterDialog = new SaveFilterDialog({
        title : 'Save Filter',
        filterView : that.filterView
      });

      this._saveFiltersButton = new Button({
        class   : 'save-filters-btn filter-btn',
        label   : 'Save',
        onClick : function () {
          that._saveFilterDialog.show();
        }
      });
      dom.place(this._saveFiltersButton.domNode, this._topBarPane);

      this._loadFilterDialog = new LoadFilterDialog({
        title : 'Load Filter',
        filterView : that.filterView
      });

      this._loadFilterButton = new Button({
        class   : 'load-filters-btn filter-btn',
        label   : 'Load',
        onClick : function () {
          that._loadFilterDialog.show();
        }
      });
      dom.place(this._loadFilterButton.domNode, this._topBarPane);
    }
  });
});