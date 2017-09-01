// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/data/ItemFileWriteStore',
  'dojo/topic',
  'dijit/form/Button',
  'dijit/form/TextBox',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dojox/grid/DataGrid',
  'codechecker/util'],
function (declare, domConstruct, ItemFileWriteStore, topic, Button,
  TextBox, BorderContainer, ContentPane, DataGrid, util) {

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
        { name : 'Last check duration', field : 'duration', styles : 'text-align: center;' }*/
      ];

      this.focused = true;
      this.selectable = true;
      this.keepSelection = true;
      this.escapeHTMLInData = false;
    },

    postCreate : function () {
      this.inherited(arguments);
      this._populateProducts();
    },

    onRowClick : function (evt) {
      var item = this.getItem(evt.rowIndex);

      switch (evt.cell.field) {
        case 'name':
          if (item.connected[0] && item.accessible[0]) {
            window.open('/' + item.endpoint[0], '_self');
          }
          break;
      }
    },

    getItemsWhere : function (func) {
      var result = [];

      for (var i = 0; i < this.rowCount; ++i) {
        var item = this.getItem(i);
        if (func(item))
          result.push(item);
      }

      return result;
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
          statusIcon = '<abbr class="customIcon product-error"></abbr>';
          description = '<span class="product-description-error database">'
            + 'The database connection for this product could not be made!'
            + '</span><br />' + description;
        } else if (!item.accessible) {
          statusIcon = '<abbr class="customIcon product-noaccess"></abbr>';
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
        endpoint : item.endpoint,
        name : name,
        description : description,
        connected : item.connected,
        accessible : item.accessible
      });
    },

    _populateProducts : function (productNameFilter) {
      var that = this;

      PROD_SERVICE.getProducts(null, productNameFilter, function (productList) {
        that.onLoaded(productList);

        productList.forEach(function (item) {
          that._addProductData(item);
        });
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
          products.forEach(function (products) {
            that.store.deleteItem(products);
          });
          that.store.save();
        }
      });

      PROD_SERVICE.getProducts(null, productNameFilter, function (productDataList) {
        productDataList.forEach(function (item) {
          that._addProductData(item);
        });
      });
    },

    onLoaded : function (productDataList) {}
  });

  var ProductFilter = declare(ContentPane, {
    constructor : function () {
      var that = this;

      this._productFilter = new TextBox({
        id          : 'products-filter',
        placeHolder : 'Search for products...',
        onKeyUp    : function (evt) {
          clearTimeout(this.timer);

          var filter = this.get('value');
          this.timer = setTimeout(function () {
            that.listOfProductsGrid.refreshGrid(filter);
          }, 500);
        }
      });
    },

    postCreate : function () {
      this.addChild(this._productFilter);
    }
  });

  return declare(BorderContainer, {
    postCreate : function () {
      var that = this;

      var filterPane = new ProductFilter({
        id : 'products-filter-container',
        region : 'top'
      });

      var listOfProductsGrid = new ListOfProductsGrid({
        id : 'productGrid',
        region : 'center',
        onLoaded : that.onLoaded
      });

      filterPane.set('listOfProductsGrid', listOfProductsGrid);

      this.addChild(filterPane);
      this.addChild(listOfProductsGrid);
    },

    onLoaded : function (productDataList) {}
  });
});
