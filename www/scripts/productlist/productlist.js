// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/topic',
  'dojo/dom-construct',
  'dijit/form/Button',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dijit/layout/TabContainer',
  'codechecker/hashHelper',
  'codechecker/HeaderMenu',
  'products/ListOfProducts'],
function (declare, topic, domConstruct, Button, BorderContainer, ContentPane,
  TabContainer, hashHelper, HeaderMenu, ListOfProducts) {

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

    var headerPane = new ContentPane({ id : 'headerPane', region : 'top' });
    layout.addChild(headerPane);

    var productsPane = new ContentPane({
      title : 'All products',
      region : 'center'
    });
    productsTab.addChild(productsPane);

    //--- Logo ---//

    var logoContainer = domConstruct.create('div', {
      id : 'logo-container'
    }, headerPane.domNode);

    var logo = domConstruct.create('span', { id : 'logo' }, logoContainer);

    var logoText = domConstruct.create('div', {
      id : 'logo-text',
      innerHTML : 'CodeChecker ' + CC_PROD_SERVICE.getPackageVersion()
    }, logoContainer);

    var title = domConstruct.create('span', {
      id : 'logo-title',
      innerHTML : "Products on this server"
    }, logoText);

    var user = CC_AUTH_SERVICE.getLoggedInUser();
    var loginUserSpan = null;
    if (user.length > 0) {
      loginUserSpan = domConstruct.create('span', {
        id: 'loggedin',
        innerHTML: "Logged in as " + user + "."
      });
    }

    //--- Admin button ---//

    layout.set('adminLevel', 0);

    var isSuperuser = CC_AUTH_SERVICE.hasPermission(
      Permission.SUPERUSER, "");

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

    var headerMenu = domConstruct.create('div', {
        id : 'header-menu'
    });

    var headerMenuButton = new HeaderMenu({
      class : 'main-menu-button',
      iconClass : 'dijitIconFunction',
    });

    if (loginUserSpan != null)
        domConstruct.place(loginUserSpan, headerMenu);

    if (isSuperuser || isAdminOfAnyProduct)
      domConstruct.place(menuButton.domNode, headerMenu);

    domConstruct.place(headerMenuButton.domNode, headerMenu);
    domConstruct.place(headerMenu, headerPane.domNode);

    //--- Center panel ---//

    var listOfProducts = new ListOfProducts({
      title : 'Products'
    });

    productsPane.addChild(listOfProducts);

    topic.subscribe('tab/userguide', function () {
      var that = this;

      if (!this.userguide) {
        this.userguide = new ContentPane({
          title : 'User guide',
          closable : true,
          href  : 'userguide/doc/html/md_userguide.html',
          onClose : function () {
            delete that.userguide;
            return true;
          },
          onShow : function () {
            hashHelper.resetStateValues({
              'tab' : 'userguide'
            });
          }
        });
        productsTab.addChild(this.userguide);
      }

      hashHelper.resetStateValues({
        'tab' : 'userguide'
      });
      productsTab.selectChild(this.userguide);
    });

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();
  };
});
