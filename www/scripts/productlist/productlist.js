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
  'products/ListOfProducts'],
function (declare, topic, domConstruct, Button, BorderContainer,
  ContentPane, ListOfProducts) {

  return function () {

    //---------------------------- Global objects ----------------------------//

    CC_PROD_SERVICE =
      new codeCheckerProductManagement.codeCheckerProductServiceClient(
        new Thrift.Protocol(new Thrift.Transport("Products")));

    CC_PROD_OBJECTS = codeCheckerProductManagement;

    CC_AUTH_SERVICE =
      new codeCheckerAuthentication.codeCheckerAuthenticationClient(
        new Thrift.TJSONProtocol(
          new Thrift.Transport("/Authentication")));

    //----------------------------- Main layout ------------------------------//

    var layout = new BorderContainer({ id : 'mainLayout' });

    var headerPane = new ContentPane({ id : 'headerPane', region : 'top' });
    layout.addChild(headerPane);

    var productsPane = new ContentPane({ region : 'center' });
    layout.addChild(productsPane);

    //--- Logo ---//

    var logoContainer = domConstruct.create('div', {
      id : 'logo-container'
    }, headerPane.domNode);

    var logo = domConstruct.create('span', { id : 'logo' }, logoContainer);

    var logoText = domConstruct.create('div', {
      id : 'logo-text',
      innerHTML : 'CodeChecker - Products on this server'
    }, logoContainer);

    var version = domConstruct.create('span', {
      id : 'logo-version',
      innerHTML : CC_PROD_SERVICE.getPackageVersion()
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

    layout.set('isAdmin', false);

    // TODO: Show admin button only if superuser.
    var menuButton = new Button({
      class : 'mainMenuButton adminButton',
      label : "Show administration",
      onClick : function () {
        // TODO: Query if user can be superadmin and only allow this if so.

        var isAdmin = !layout.get('isAdmin');

        layout.set('isAdmin', isAdmin);
        listOfProducts.setAdmin(isAdmin);
        this.set('label',
                 (isAdmin ? 'Hide' : 'Show') + ' administration');
      }
    });

    var headerMenu = domConstruct.create('div', {
        id : 'header-menu'
      });

    if (loginUserSpan != null)
        domConstruct.place(loginUserSpan, headerMenu);

    domConstruct.place(menuButton.domNode, headerMenu);

    domConstruct.place(headerMenu, headerPane.domNode);

    //--- Center panel ---//

    var listOfProducts = new ListOfProducts({
      title : 'Products'
    });

    productsPane.addChild(listOfProducts);

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();
  };
});
