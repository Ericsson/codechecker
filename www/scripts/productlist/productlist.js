// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dijit/form/Button',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dijit/layout/TabContainer',
  'codechecker/HeaderPane',
  'codechecker/TabCount',
  'products/ListOfProducts'],
function (declare, Button, BorderContainer, ContentPane, TabContainer,
  HeaderPane, TabCount, ListOfProducts) {

  return function () {

    //---------------------------- Global objects ----------------------------//

    CC_PROD_SERVICE =
      new codeCheckerProductManagement_v6.codeCheckerProductServiceClient(
        new Thrift.Protocol(new Thrift.Transport(
          "v" + CC_API_VERSION + "/Products")));

    CC_PROD_OBJECTS = codeCheckerProductManagement_v6;

    CC_AUTH_SERVICE =
      new codeCheckerAuthentication_v6.codeCheckerAuthenticationClient(
        new Thrift.TJSONProtocol(
          new Thrift.Transport("/v" + CC_API_VERSION + "/Authentication")));

    CC_AUTH_OBJECTS = codeCheckerAuthentication_v6;

    //----------------------------- Main layout ------------------------------//

    var layout = new BorderContainer({ id : 'mainLayout' });

    var productsTab = new TabContainer({ region : 'center' });
    layout.addChild(productsTab);

    var productsPane = new (declare([ContentPane, TabCount], {
      title : 'All products',
      region : 'center'
    }));

    productsTab.addChild(productsPane);

    //--- Center panel ---//

    var listOfProducts = new ListOfProducts({
      title : 'Products',
      id : 'list-of-products',
      productsPane : productsPane
    });

    productsPane.addChild(listOfProducts);

    //--- Admin button ---//

    layout.set('adminLevel', 0);

    var isSuperuser = CC_AUTH_SERVICE.hasPermission(Permission.SUPERUSER, "");
    var isAdminOfAnyProduct = CC_PROD_SERVICE.isAdministratorOfAnyProduct();

    var menuButton = new Button({
      class : 'main-menu-button admin-button',
      label : "Show administration",
      onClick : function () {
        var adminLevel = layout.get('adminLevel');

        if (adminLevel)
          adminLevel = 0;
        else {
          if (isAdminOfAnyProduct)
            adminLevel = 1;
          if (isSuperuser)
            adminLevel = 2;
        }

        layout.set('adminLevel', adminLevel);
        listOfProducts.setAdmin(adminLevel);
        this.set('label',
                 (adminLevel > 0 ? 'Hide' : 'Show') + ' administration');
      }
    });

    var headerPane = new HeaderPane({
      id : 'headerPane',
      title : "Products on this server",
      region : 'top',
      menuItems : isSuperuser || isAdminOfAnyProduct
                ? [ menuButton.domNode ]
                : null,
      mainTab : productsTab
    });
    layout.addChild(headerPane);

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();
  };
});
