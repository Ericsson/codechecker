// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/cookie',
  'dojo/dom',
  'dojo/dom-construct',
  'dojo/dom-class',
  'dojo/io-query',
  'dojo/keys',
  'dojo/on',
  'dijit/form/Button',
  'dijit/form/TextBox',
  'dijit/layout/BorderContainer',
  'dijit/layout/ContentPane',
  'dojox/widget/Standby',
  'codechecker/MessagePane',
  'codechecker/hashHelper'],
function (declare, cookie, dom, domConstruct, domClass, ioQuery, keys, on,
  Button, TextBox, BorderContainer, ContentPane, Standby, MessagePane, hash) {

  // A stripped-down version of the "normal" CodeChecker GUI header, tailored
  // for a lightweight login window.
  var HeaderPane = declare(ContentPane, {
    postCreate : function () {
      this.inherited(arguments);

      //--- Logo ---//

      var logoContainer = domConstruct.create('div', {
        id : 'logo-container'
      }, this.domNode);

      domConstruct.create('span', { id : 'logo' }, logoContainer);

      domConstruct.create('div', {
        id : 'logo-text',
        innerHTML : 'CodeChecker'
      }, logoContainer);
    }
  });

  var LoginPane = declare(ContentPane, {
    _doLogin : function() {
      var that = this;

      // No username supplied.
      if (!this.txtUser.value || !this.txtUser.value.trim().length) {
        domClass.add(that._mbox.domNode, 'mbox-error');
        that._mbox.show("Failed to log in!", "No username supplied.");
        return;
      }

      this.set('isAlreadyLoggingIn', true);
      this._standBy.show();

      CC_AUTH_SERVICE.performLogin(
        'Username:Password', this.txtUser.value + ':' + this.txtPass.value,
        function (sessionToken) {
          domClass.add(that._mbox.domNode, 'mbox-success');
          that._mbox.show("Successfully logged in!", '');

          // Set the cookie in the browser.
          cookie(CC_AUTH_COOKIE_NAME, sessionToken, { path : '/' });

          var state = hash.getState();

          var search = window.location.search;
          if (search.charAt(0) === '?')
            search = search.substring(1);

          var searchParams = ioQuery.queryToObject(search);
          var returnTo = searchParams['returnto'] || '';

          window.location = window.location.origin + '/' + returnTo + '#'
            + ioQuery.objectToQuery(state);
        }).fail(function (jsReq, status, exc) {
          if (status === "parsererror") {
            that._standBy.hide();
            domClass.add(that._mbox.domNode, 'mbox-error');
            that._mbox.show("Failed to log in!", exc.message);

            that.txtPass.set('value', '');
            that.txtPass.focus();
            that.set('isAlreadyLoggingIn', false);
          }
        });
    },

    constructor : function() {
      this._mbox = new MessagePane({
        class   : 'mbox'
      });

      this.txtUser = new TextBox({
        class : 'form-input',
        name  : 'username'
      });

      this.txtPass = new TextBox({
        class : 'form-input',
        name  : 'password',
        type  : 'password'
      });

      var that = this;
      this.btnSubmit = new Button({
        label   : "Login",
        onClick : function () {
          if (!that.get('isAlreadyLoggingIn'))
            that._doLogin();
        }
      });
    },

    postCreate : function() {
      this.set('isAlreadyLoggingIn', false);

      this.addChild(this._mbox);
      this._mbox.hide();

      this._standBy = new Standby({
        color : '#ffffff',
        target : this.domNode,
        duration : 0
      });
      this.addChild(this._standBy);

      var authParams = CC_AUTH_SERVICE.getAuthParameters();

      if (!authParams.requiresAuthentication || authParams.sessionStillActive) {
        domClass.add(this._mbox.domNode, 'mbox-success');

        var message = '';
        if (!authParams.requiresAuthentication)
          message = "This server allows anonymous access.";
        else if (authParams.sessionStillActive)
          message = "You are already logged in.";
        this._mbox.show("No authentication required.", message);

        var returnTo = hash.getState('returnto') || '';
        window.location = window.location.origin + '/' + returnTo;
      } else {
        var authMethods = CC_AUTH_SERVICE.getAcceptedAuthMethods();
        if (authMethods.indexOf('Username:Password') === -1) {
          domClass.add(this._mbox.domNode, 'mbox-error');
          this._mbox.show("Server rejects username-password authentication!",
                          "This login form cannot be used.");
        } else {
          var cntPrompt = domConstruct.create('div', {
            class : 'formElement'
          }, this.containerNode);
          domConstruct.create('span', {
            class     : 'login-prompt',
            style     : 'width: 100%',
            innerHTML : this.loginPrompt
          }, cntPrompt);

          // Render the login dialog's controls.

          var cntUser = domConstruct.create('div', {
            class : 'formElement'
          }, this.containerNode);
          domConstruct.create('label', {
            class     : 'formLabel bold',
            innerHTML : "Username: ",
            for       : 'username'
          }, cntUser);
          domConstruct.place(this.txtUser.domNode, cntUser);

          var cntPass = domConstruct.create('div', {
            class : 'formElement'
          }, this.containerNode);
          domConstruct.create('label', {
            class     : 'formLabel bold',
            innerHTML : "Password: ",
            for       : 'password'
          }, cntPass);
          domConstruct.place(this.txtPass.domNode, cntPass);

          var cntLogin = domConstruct.create('div', {
            class : 'formElement'
          }, this.containerNode);
          domConstruct.place(this.btnSubmit.domNode, cntLogin);

          var that = this;
          function keypressHandler(evt) {
            if (!that.get('isAlreadyLoggingIn') &&
                evt.keyCode === keys.ENTER) {
              that.btnSubmit.focus();
              that._doLogin();
            }
          }
          on(this.txtUser.domNode, 'keypress', keypressHandler);
          on(this.txtPass.domNode, 'keypress', keypressHandler);
          on(this.btnSubmit.domNode, 'keypress', keypressHandler);
        }
      }
    }
  });

  return function () {

    //---------------------------- Global objects ----------------------------//

    CC_AUTH_SERVICE =
      new codeCheckerAuthentication_v6.codeCheckerAuthenticationClient(
        new Thrift.TJSONProtocol(
          new Thrift.Transport("/v" + CC_API_VERSION + "/Authentication")));

    CC_AUTH_OBJECTS = codeCheckerAuthentication_v6;

    //----------------------------- Main layout ------------------------------//

    var layout = new BorderContainer({ id : 'mainLayout' });

    var headerPane = new HeaderPane({
      id : 'headerPane',
      region : 'top'
    });
    layout.addChild(headerPane);

    //--- Center panel ---//

    var that = this;

    this.loginPane = new LoginPane({
      region      : 'center',

      // TODO: Extend the API so that custom messages can be shown here.
      loginPrompt : "Accessing this CodeChecker server requires authentication!"
    });

    var loginContainer = new ContentPane({
      region : 'center',
      postCreate : function () {
         var smallerContainer = domConstruct.create('div', {
           id : 'login-form'
         }, this.containerNode);

         domConstruct.place(that.loginPane.domNode, smallerContainer);
      }
    });

    layout.addChild(loginContainer);

    //--- Init page ---//

    document.body.appendChild(layout.domNode);
    layout.startup();
  };
});
