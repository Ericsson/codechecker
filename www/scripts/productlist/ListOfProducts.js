// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-class',
  'dojo/dom-construct',
  'dojo/data/ItemFileWriteStore',
  'dojo/topic',
  'dojox/grid/DataGrid',
  'dijit/ConfirmDialog',
  'dijit/form/Button',
  'dijit/form/TextBox',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'codechecker/util',
  'products/ProductSettingsView'],
function (declare, domClass, domConstruct, ItemFileWriteStore, topic,
  DataGrid, ConfirmDialog, Button, TextBox, BorderContainer, ContentPane,
  util, ProductSettingsView) {

  //--- Product delete confirmation dialog ---//

  var DeleteProductDialog = declare(ConfirmDialog, {
    constructor : function () {
      this._confirmLabel = new ContentPane({
        class : 'deleteConfirmText',
        innerHTML : '<span class="warningHeader">You have selected to ' +
                    'delete a product!</span><br \><br \>' +
                    "Deleting a product <strong>will</strong> remove " +
                    "product-specific configuration, such as access " +
                    "control and authorisation settings, and " +
                    "<strong>will</strong> disconnect the database from " +
                    "the server.<br \><br \>Analysis results stored in " +
                    "the database <strong>will NOT</strong> be lost!"
      });
    },

    onCancel : function () {
      this.productGrid.set('deleteProductID', null);
    },

    onExecute : function () {
      var that = this;

      // TODO: Check if the user is superadmin, before calling the API.
      if (this.productGrid.deleteProductID) {
        CC_PROD_SERVICE.removeProduct(
          this.productGrid.deleteProductID,
          function (success) {
            that.productGrid.store.fetch({
              onComplete : function (products) {
                products.forEach(function (product) {
                  if (product.id[0] === that.productGrid.deleteProductID)
                    that.productGrid.store.deleteItem(product);
                });
              }
            });
          });
      }
    },

    postCreate : function () {
      this.inherited(arguments);
      this.connect(this.content.cancelButton, "onClick", "onCancel");

      this.addChild(this._confirmLabel);
    }
  });

  //--- Product grid ---//

  var ListOfProductsGrid = declare(DataGrid, {
    constructor : function () {
      this.store = new ItemFileWriteStore({
        data : { identifier : 'endpoint', items : [] }
      });

      // TODO: Support access control for products and handle locks well.
      // TODO: Support showing the last checkin's information for products.
      this.structure = [
        { name : '&nbsp;', field : 'status', cellClasses : 'status', width : '20px', noresize : true },
        { name : '&nbsp;', field : 'icon', cellClasses : 'product-icon', width : '40px', noresize : true },
        { name : 'Name', field : 'name', cellClasses : 'product-name', width : '25%' },
        { name : 'Description', field : 'description', styles : 'text-align: left;', width : '70%' }/*,
        { name : 'Last check date', field : 'date', styles : 'text-align: center;', width : '30%' },
        { name : 'Last check bugs', field : 'numberofbugs', styles : 'text-align: center;', width : '20%' },
        { name : 'Last check duration', field : 'duration', styles : 'text-align: center;' }*/,
        { name : '&nbsp;', field : 'editIcon', cellClasses : 'status', width : '20px', noresize : true},
        { name : '&nbsp;', field : 'deleteIcon', cellClasses : 'status', width : '20px', noresize : true}
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;
      this.sortInfo = '+3';
    },

    postCreate : function () {
      this.inherited(arguments);
      this._populateProducts();
    },

    canSort : function (inSortInfo) {
      var cell = this.getCell(Math.abs(inSortInfo) - 1);

      return cell.field === 'name' || cell.field === 'description';
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);

      switch (evt.cell.field) {
        case 'name':
          if (item.connected[0] && item.accessible[0]) {
            window.open('/' + item.endpoint[0], '_self');
          }
          break;
        case 'editIcon':
          // TODO: Check if user has rights to edit, and if admin was toggled.
          if (this.isAdmin) {
            this.productSettingsView.set(
              'title', "Edit product '" + item.endpoint[0] + "'");
            this.productSettingsView.set('settingsMode', 'edit');
            this.productSettingsView.setProductConfig(new PROD_OBJECTS.ProductConfiguration());
            this.productSettingsView.set('successCallback', function () {
              // Reapply the product list filtering.
              this.infoPane._executeFilter(
                this.infoPane._productFilter.get('value'));
            });

            this.productSettingsView.show();
          }
          break;
        case 'deleteIcon':
          // TODO: Check if user is superuser to delete.
          if (this.isAdmin) {
            this.set('deleteProductID', item.id[0]);
            this.confirmDeleteDialog.show();
          }
          break;
      }
    },

    _addProductData : function (item) {
      var name = util.atou(item.displayedName_b64);
      var description = item.description_b64
                      ? util.atou(item.description_b64)
                      : "";
      var statusIcon = '';
      var icon ='<div class="product-avatar" '
        + 'style="background-color: '
        + util.strToColorBlend(item.endpoint, "white", 0.75).toHex() + '">'
        + '<span class="product-avatar">'
        + name[0].toUpperCase()
        + '</span></div>';

      if (!item.connected || !item.accessible) {
        name = '<span class="product-error">'
          + name + '</span>';

        if (!item.connected) {
          statusIcon = '<span class="customIcon product-error"></span>';
          description = '<span class="product-description-error database">'
            + 'The database connection for this product could not be made!'
            + '</span><br />' + description;
        } else if (!item.accessible) {
          statusIcon = '<span class="customIcon product-noaccess"></span>';
          description = '<span class="product-description-error access">'
            + 'You do not have access to this product!'
            + '</span><br />' + description;
        }
      } else {
        name = '<span class="link">' + name + '</span>';
      }

      this.store.newItem({
        status : statusIcon,
        icon : icon,
        id : item.id,
        endpoint : item.endpoint,
        name : name,
        description : description,
        connected : item.connected,
        accessible : item.accessible,
        editIcon : '',
        deleteIcon : ''
      });
    },

    _populateProducts : function (productNameFilter) {
      var that = this;

      CC_PROD_SERVICE.getProducts(null, productNameFilter,
      function (productList) {
        that.onLoaded(productList);

        productList.forEach(function (item) {
          that._addProductData(item);
        });

        that.onLoaded(productList);
      });
    },

    /**
     * This function refreshes grid with available product data based on
     * text name filter.
     */
    refreshGrid : function (productNameFilter) {
      var that = this;

      this.store.fetch({
        onComplete : function (products) {
          products.forEach(function (product) {
            that.store.deleteItem(product);
          });
          that.store.save();
        }
      });

      CC_PROD_SERVICE.getProducts(null, productNameFilter,
      function (productDataList) {
        productDataList.forEach(function (item) {
          that._addProductData(item);
        });

        that.onLoaded(productDataList);
      });
    },

    toggleAdminButtons : function (isAdmin) {
      this.set('isAdmin', isAdmin);
      var that = this;

      this.store.fetch({
        onComplete : function (products) {
          products.forEach(function (product) {
            if (isAdmin) {
              that.store.setValue(product, 'editIcon',
                '<span class="customIcon product-edit"></span>');
              that.store.setValue(product, 'deleteIcon',
                '<span class="customIcon product-delete"></span>');
            } else {
              that.store.setValue(product, 'editIcon', '');
              that.store.setValue(product, 'deleteIcon', '');
            }
          });
        }
      });
    },

    onLoaded : function (productDataList) {
      this.toggleAdminButtons(this.isAdmin);
      this.sort();
    }
  });

  //--- Grid top bar ---//

  var ProductInfoPane = declare(ContentPane, {
    _executeFilter : function (filter) {
      var that = this;

      clearTimeout(this._timer);
      this._timer = setTimeout(function () {
        that.listOfProductsGrid.refreshGrid(filter);
      }, 500);
    },

    constructor : function () {
      var that = this;

      //--- Product filter ---//

      this._productFilter = new TextBox({
        placeHolder : 'Search for products...',
        onKeyUp    : function (evt) {
          that._executeFilter(this.get('value'));
        }
      });

      //--- New product Button ---//

      this._newBtn = new Button({
        label    : 'Create new product',
        class    : 'new-btn',
        onClick  : function () {
          that.productSettingsView.set('title', "Add new product");
          that.productSettingsView.set('settingsMode', 'add');
          that.productSettingsView.set('successCallback', function () {
            // Reapply the product list filtering.
            that._executeFilter(that._productFilter.get('value'));
          });

          that.productSettingsView.show();
        }
      });
    },

    postCreate : function () {
      this.addChild(this._productFilter);
      this.addChild(this._newBtn);

      // By default, the create button should be invisible.
      domClass.add(this._newBtn.domNode, 'invisible');
    },

    toggleAdminButtons : function (isAdmin) {
      this.set('isAdmin', isAdmin);

      if (!isAdmin)
        domClass.add(this._newBtn.domNode, 'invisible');
      else
        domClass.remove(this._newBtn.domNode, 'invisible');
    }
  });

  //--- Main view ---//

  return declare(BorderContainer, {
    postCreate : function () {
      var infoPane = new ProductInfoPane({
        region : 'top'
      });

      this.set('infoPane', infoPane);

      var listOfProductsGrid = new ListOfProductsGrid({
        id : 'productGrid',
        region : 'center'
      });
      
      this.set('listOfProductsGrid', listOfProductsGrid);
      infoPane.set('listOfProductsGrid', listOfProductsGrid);
      listOfProductsGrid.set('infoPane', infoPane);

      this.addChild(infoPane);
      this.addChild(listOfProductsGrid);

      //--- Initialise auxiliary GUI elements ---//

      var confirmDeleteDialog = new DeleteProductDialog({
        title       : 'Confirm deletion of product',
        productGrid : listOfProductsGrid
      });

      listOfProductsGrid.set('confirmDeleteDialog', confirmDeleteDialog);

      var productSettingsView = new ProductSettingsView({
        title       : 'Product settings',
        productGrid : listOfProductsGrid,
        style       : 'width: 650px'
      });

      infoPane.set('productSettingsView', productSettingsView);
      listOfProductsGrid.set('productSettingsView', productSettingsView);
    },

    setAdmin : function (isAdmin) {
      this.infoPane.toggleAdminButtons(isAdmin);
      this.listOfProductsGrid.toggleAdminButtons(isAdmin);
    }
  });
});
