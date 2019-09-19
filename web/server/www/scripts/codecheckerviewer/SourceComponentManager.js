// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/dom-attr',
  'dojo/dom-class',
  'dojo/_base/declare',
  'dojo/data/ItemFileWriteStore',
  'dojox/grid/DataGrid',
  'dijit/ConfirmDialog',
  'dijit/form/Button',
  'dijit/form/SimpleTextarea',
  'dijit/form/TextBox',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'codechecker/util'],
function (dom, domAttr, domClass, declare, ItemFileWriteStore, DataGrid,
  ConfirmDialog, Button, SimpleTextarea, TextBox, BorderContainer,
  ContentPane, util) {

  var DeleteComponentDialog = declare(ConfirmDialog, {
    constructor : function () {
      this._confirmLabel = new ContentPane({
        class : 'delete-confirm-text',
        innerHTML : '<span class="warningHeader">You have selected to ' +
                    'delete a source component!</span>'
      });
    },

    postCreate : function () {
      this.inherited(arguments);
      this.addChild(this._confirmLabel);
    },

    onExecute : function () {
      try {
        CC_SERVICE.removeSourceComponent(this.componentName);
      } catch (ex) { util.handleThriftException(ex); }

      this.listSourceComponent.refreshGrid();
    }
  });

  var EditSourceComponent = declare(ContentPane, {
    postCreate : function () {
      var that = this;

      this._errorMessage = dom.create('div', {class : 'mbox mbox-error hide'});
      dom.place(this._errorMessage, this.domNode);

      this._componentName = new TextBox({
        class : 'component-name',
        placeHolder : 'Name of the source component...'
      });
      this._placeFormElement(this._componentName, 'name', 'Name*');

      this._componentValue = new SimpleTextarea({
        class : 'component-value',
        rows : 10,
        placeholder : 'Value of the source component.\nEach line must start '
                    + 'with a "+" (results from this path should be listed) or '
                    + 'a "-" (results from this path should not be listed) '
                    + 'sign.\nFor whole directories, a trailing "*" must be '
                    + 'added.\nE.g.: +/a/b/x.cpp or -/a/b/*'
      });
      this._placeFormElement(this._componentValue, 'value', 'Value*');

      this._componentDescription = new TextBox({
        class : 'component-description',
        placeHolder : 'Description of the source component...'
      });
      this._placeFormElement(this._componentDescription, 'description',
        'Description');

      this._btnCreate  = new Button({
        class   : 'btn-save',
        label   : 'Save',
        onClick : function () {
          var componentName = that._componentName.get('value');
          if (!componentName) {
            return that.showError('Component name can not be empty!');
          }

          var componentValue = that._componentValue.get('value');
          if (!componentValue) {
            return that.showError('Component value can not be empty!');
          }

          if (!that.isValidComponentValue(componentValue)) {
            return that.showError('Component value format is invalid! Every '
              + 'line should start with + or - sign followed by one or more '
              + 'character.');
          }

          var componentDescription = that._componentDescription.get('value');

          // Remove the original component because the user would like to change
          // the name.
          var origComponentName = that._origComponent
            ? that._origComponent.name[0]
            : null;

          if (origComponentName && origComponentName !== componentName) {
            try {
              CC_SERVICE.removeSourceComponent(origComponentName);
            } catch (ex) { util.handleThriftException(ex); }
          }

          CC_SERVICE.addSourceComponent(componentName, componentValue,
          componentDescription, function (success) {
            if (success) {
              that.showSuccess('The component has been successfully ' +
                               'created/edited!');
              that.sourceComponentManager.updateNeeded = true;

              // Reset items of the filter tooltip.
              that.sourceComponentFilter._filterTooltip.reset();
            } else {
              that.showError('Failed to create/edit component!');
            }
          }).fail(function (jsReq, status, exc) {
            if (status === 'parsererror') {
              that.showError(exc.message);
              util.handleAjaxFailure(jsReq);
            }
          });
        }
      });
      this.addChild(this._btnCreate);
    },

    isValidComponentValue : function (value) {
      var lines = value.split(/\r|\n/);
      for (var i = 0; i < lines.length; ++i) {
        if (!lines[i].startsWith('+') && !lines[i].startsWith('-') ||
             lines[i].trim().length < 2
        ) {
          return false;
        }
      }
      return true;
    },

    hideError : function () {
      domClass.add(this._errorMessage, 'hide');
    },

    showSuccess : function (msg) {
      this._errorMessage.innerHTML = msg;
      domClass.remove(this._errorMessage, 'hide');
      domClass.remove(this._errorMessage, 'mbox-error');
      domClass.add(this._errorMessage, 'mbox-success');
    },

    showError : function (msg) {
      this._errorMessage.innerHTML = msg;
      domClass.remove(this._errorMessage, 'hide');
      domClass.remove(this._errorMessage, 'mbox-success');
      domClass.add(this._errorMessage, 'mbox-error');
    },

    _placeFormElement : function (element, key, label) {
      this.addChild(element);

      var container = dom.create('div', {
        class : 'formElement'
      }, this.containerNode);

      if (label) {
        var labelNode = dom.create('label', {
          class     : 'formLabel bold',
          innerHTML : label + ': '
        }, container);

        if (key) {
          domAttr.set(labelNode, 'for', key);
        }
      }

      dom.place(element.domNode, container);
    },

    init : function (component) {
      if (component) {
        this._componentName.set('value', component.name[0]);
        this._componentValue.set('value', component.value[0]);
        this._componentDescription.set('value', component.description[0]);
        this._origComponent = component;
      } else {
        this._componentName.set('value', null);
        this._componentValue.set('value', null);
        this._componentDescription.set('value', null);
        this._origComponent = null;
      }

      this.hideError();
    }
  });

  function componentValueFormatter(value) {
    return value.split(/\r|\n/).map(function (line) {
      if (line.startsWith('+')) {
        return '<span style="color:green">' + line + '</span>';
      } else {
        return '<span style="color:red">' + line + '</span>';
      }
    }).join('<br/>');
  }

  var ListSourceComponent = declare(DataGrid, {
    constructor : function () {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'id', items : [] }
      });

      this.structure = [
        { name : 'Name', field : 'name', styles : 'text-align: left;', width : '100%' },
        { name : 'Value', field : 'value', styles : 'text-align: left;', width : '100%', formatter: componentValueFormatter },
        { name : 'Description', field : 'description', styles : 'text-align: left;', width : '100%' },
        { name : '&nbsp;', field : 'editIcon', cellClasses : 'status', width : '20px', noresize : true },
        { name : '&nbsp;', field : 'deleteIcon', cellClasses : 'status', width : '20px', noresize : true }
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;
      this.autoHeight = false;
    },

    postCreate : function () {
      this.inherited(arguments);

      this._confirmDeleteDialog = new DeleteComponentDialog({
        title : 'Confirm deletion of component',
        listSourceComponent : this
      });
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);
      switch (evt.cell.field) {
        case 'editIcon':
          this.editComponent(item);
          break;
        case 'deleteIcon':
          this.removeComponent(item.name[0]);
          break;
      }
    },

    removeComponent : function (name) {
      this._confirmDeleteDialog.componentName = name;
      this._confirmDeleteDialog.show();
    },

    editComponent : function (component) {
      this.sourceComponentManager.showNewComponentPage(component);
    },

    refreshGrid : function () {
      var that = this;

      this.store.fetch({
        onComplete : function (sourceComponents) {
          sourceComponents.forEach(function (component) {
            that.store.deleteItem(component);
          });
          that.store.save();
        }
      });

      CC_SERVICE.getSourceComponents(null, function (sourceComponents) {
        sourceComponents.forEach(function (item) {
          that._addSourceComponent(item);
        });
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
    },

    _addSourceComponent : function (component) {
      this.store.newItem({
        id : component.name,
        name : component.name,
        value : component.value,
        description : component.description,
        editIcon : '<span class="customIcon edit"></span>',
        deleteIcon : '<span class="customIcon delete"></span>'
      });
    },

    onShow : function () {
      if (this.sourceComponentManager.updateNeeded) {
        this.refreshGrid();
        this.sourceComponentManager.updateNeeded = false;
      }
    }
  });

  return declare(ContentPane, {
    updateNeeded : true,

    postCreate : function () {
      var that = this;

      this._wrapper = new BorderContainer({
        class : 'component-manager-wrapper'
      });

      this.addChild(this._wrapper);

      this._btnNew  = new Button({
        class   : 'btn-new',
        region  : 'top',
        label   : 'New',
        onClick : function () {
          that.showNewComponentPage();
        }
      });

      this._btnBack  = new Button({
        class   : 'btn-back',
        region  : 'top',
        label   : 'Back',
        onClick : function () {
          that.showListOfComponentPage();
        }
      });

      this._editSourceComponent = new EditSourceComponent({
        region : 'center',
        sourceComponentManager : this,
        sourceComponentFilter : this.sourceComponentFilter
      });

      this._listSourceComponent = new ListSourceComponent({
        region : 'center',
        editSourceComponent : this._editSourceComponent,
        sourceComponentManager : this
      });
    },

    showNewComponentPage : function (component) {
      this._clearDom();

      this._editSourceComponent.init(component);

      this._wrapper.addChild(this._btnBack);
      this._wrapper.addChild(this._editSourceComponent);
    },

    showListOfComponentPage : function () {
      this._clearDom();

      this._wrapper.addChild(this._btnNew);
      this._wrapper.addChild(this._listSourceComponent);
      this._listSourceComponent.onShow();
    },

    refreshGrid : function () {
      this._listSourceComponent.refreshGrid();
    },

    _clearDom : function () {
      this._wrapper.getChildren().forEach(function (child) {
        this.removeChild(child);
      }, this);
    }
  });
});
