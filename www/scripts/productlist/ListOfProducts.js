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
  'dijit/Dialog',
  'dijit/form/Button',
  'dijit/form/TextBox',
  'dijit/layout/ContentPane',
  'codechecker/util',
  'products/PermissionList',
  'products/ProductSettingsView'],
function (declare, domClass, domConstruct, ItemFileWriteStore, topic,
  DataGrid, ConfirmDialog, Dialog, Button, TextBox, ContentPane, util,
  PermissionList, ProductSettingsView) {

  //--- Global (server-wide) permission configuration dialog ---//

  var SystemPermissionsDialog = declare(ConfirmDialog, {
    constructor : function () {
      this.permissionView = new PermissionList();

      this._dialog = new Dialog({
        title : "Some permission changes failed to be saved."
      });
    },

    onExecute : function () {
      var errors = [];
      var permDiff = this.permissionView.getPermissionDifference();
      permDiff.forEach(function (record) {
       try {
          if (record.action === 'ADD')
            CC_AUTH_SERVICE.addPermission(
              record.permission, record.name, record.isGroup, "");
          else if (record.action === 'REMOVE')
            CC_AUTH_SERVICE.removePermission(
              record.permission, record.name, record.isGroup, "");
        }
        catch (exc) {
          errors.push(record);
        }
      });

      if (errors.length > 0) {
        var text = "<ul>";
        errors.forEach(function(record) {
          var permissionName = util.enumValueToKey(Permission,
                                                   record.permission);
          text += '<li><strong>' + (record.action === 'ADD' ? "Add" : "Remove") +
                  '</strong> permission <strong>' + permissionName +
                  '</strong> of ' + (record.isGroup ? "group" : "user") +
                  ' <strong>' + record.name + '</strong>.</li>\n';
        });
        text += '</ul>';
        this._dialog.set('content', text);
        this._dialog.show();
      }
    },

    populatePermissions : function() {
      this.permissionView.populatePermissions('SYSTEM', {});
    },

    postCreate : function () {
      this.inherited(arguments);
      this.addChild(this.permissionView);
    }
  });

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
        { name : 'Description', field : 'description', styles : 'text-align: left;', width : '70%' },
        { name : 'Admins', field : 'admins', styles : 'text-align: left;', width : '70%' },
        { name : 'Number of runs', field : 'runCount', styles : 'text-align: center;', width : '25%' },
        { name : 'Latest store to product', field : 'latestStoreToProduct', styles : 'text-align: center;', width : '25%' }/*,,
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

      return cell.field === 'name' ||
             cell.field === 'description' ||
             cell.field === 'runCount' ||
             cell.field === 'latestStoreToProduct';
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);
      switch (evt.cell.field) {
        case 'name':
          if (item.databaseStatus[0] === DBStatus.OK && item.accessible[0]) {
            window.open('/' + item.endpoint[0], '_self');
          }
          break;
        case 'editIcon':
          if (this.adminLevel >= 1 && item.administrating[0]) {
            // User needs to have at least PRODUCT_ADMIN level and the admin
            // options turned on, and must also be an admin of the product
            // clicked.
            var that = this;
            that.productSettingsView.setMode(
              that.get('adminLevel'), 'edit', item.id[0],
              function () {
                // Reapply the product list filtering.
                that.infoPane._executeFilter(
                  that.infoPane._productFilter.get('value'));
            });

            this.productSettingsView.show();
          }
          break;
        case 'deleteIcon':
          if (this.adminLevel >= 2) { // at least SUPERUSER
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

      var dbStatus = item.databaseStatus;

      dbStatusMsg = util.dbStatusFromCodeToString(dbStatus);

      if (dbStatus !== DBStatus.OK || !item.accessible) {
        name = '<span class="product-error">'
          + name + '</span>';

        if (!item.accessible) {
          statusIcon = '<span class="customIcon product-noaccess"></span>';
          description = '<span class="product-description-error access">'
            + 'You do not have access to this product!'
            + '</span><br />' + description;
        } else if (dbStatus !== DBStatus.OK) {

          var upgradeMsg = '';
          statusIcon = '<span class="customIcon product-error"></span>';

          if(dbStatus === DBStatus.SCHEMA_MISMATCH_OK ||
             dbStatus === DBStatus.SCHEMA_MISSING){
            upgradeMsg = ' (use <kbd>server</kbd> command for schema '
                          + 'upgrade/initialization)';
          }

          description = '<span class="product-description-error database">'
          + dbStatusMsg + upgradeMsg + '</span><br />' + description ;

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
        databaseStatus : item.databaseStatus,
        accessible : item.accessible,
        administrating : item.administrating,
        runCount : item.databaseStatus === DBStatus.OK ? item.runCount : 0,
        admins : item.admins ? item.admins.join(', ') : null,
        latestStoreToProduct : util.prettifyDate(item.latestStoreToProduct),
        editIcon : '',
        deleteIcon : ''
      });
    },

    _populateProducts : function (productNameFilter) {
      var that = this;

      CC_PROD_SERVICE.getProducts(null, productNameFilter,
      function (productList) {
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

    toggleAdminButtons : function (adminLevel) {
      this.set('adminLevel', adminLevel);
      var that = this;

      this.store.fetch({
        onComplete : function (products) {
          products.forEach(function (product) {
            if (adminLevel >= 1 && product.administrating[0])
              that.store.setValue(product, 'editIcon',
                '<span class="customIcon product-edit"></span>');
            else
              that.store.setValue(product, 'editIcon', '');

            if (adminLevel >= 2)
              that.store.setValue(product, 'deleteIcon',
                '<span class="customIcon product-delete"></span>');
            else
              that.store.setValue(product, 'deleteIcon', '');
          });
        }
      });
    },

    onLoaded : function (productDataList) {
      var that = this;

      this.toggleAdminButtons(this.adminLevel);
      setTimeout(function () { that.sort(); }, 0);
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

      //--- Edit permissions button ---//

      this._sysPermsBtn = new Button({
        label    : 'Edit global permissions',
        class    : 'system-perms-btn',
        onClick  : function () {
          that.systemPermissionsDialog.populatePermissions();
          that.systemPermissionsDialog.show();
        }
      });

      //--- New product button ---//

      this._newBtn = new Button({
        label    : 'Create new product',
        class    : 'new-btn',
        onClick  : function () {
          that.productSettingsView.setMode(
            that.get('adminLevel'), 'add', null,
            function () {
              // Reapply the product list filtering.
              that._executeFilter(that._productFilter.get('value'));

              // When a product is successfully added, hide the dialog.
              that.productSettingsView.hide();
          });
          that.productSettingsView.show();
        }
      });
    },

    postCreate : function () {
      this.addChild(this._productFilter);
      this.addChild(this._newBtn);
      this.addChild(this._sysPermsBtn);

      // By default, the administrative buttons should be invisible.
      domClass.add(this._newBtn.domNode, 'invisible');
      domClass.add(this._sysPermsBtn.domNode, 'invisible');
    },

    toggleAdminButtons : function (adminLevel) {
      this.set('adminLevel', adminLevel);

      // Permissions and new product can only be clicked if SUPERUSER.
      domClass.toggle(this._sysPermsBtn.domNode, 'invisible', adminLevel < 2);
      domClass.toggle(this._newBtn.domNode, 'invisible', adminLevel < 2);
    }
  });

  //--- Main view ---//

  return declare(ContentPane, {
    postCreate : function () {
      var infoPane = new ProductInfoPane({
        id : 'product-infopane'
      });

      this.set('infoPane', infoPane);

      var listOfProductsGrid = new ListOfProductsGrid({ id : 'productGrid' });
      
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
        productGrid : listOfProductsGrid
      });

      infoPane.set('productSettingsView', productSettingsView);
      listOfProductsGrid.set('productSettingsView', productSettingsView);

      var systemPermissionsDialog = new SystemPermissionsDialog({
        title  : 'Global permissions'
      });

      infoPane.set('systemPermissionsDialog', systemPermissionsDialog);
    },

    setAdmin : function (adminLevel) {
      this.infoPane.toggleAdminButtons(adminLevel);
      this.listOfProductsGrid.toggleAdminButtons(adminLevel);
    }
  });
});
