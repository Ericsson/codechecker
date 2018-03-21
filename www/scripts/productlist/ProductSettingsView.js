// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-attr',
  'dojo/dom-class',
  'dojo/dom-construct',
  'dijit/Dialog',
  'dijit/form/Button',
  'dijit/form/NumberTextBox',
  'dijit/form/RadioButton',
  'dijit/form/SimpleTextarea',
  'dijit/form/TextBox',
  'dijit/form/ValidationTextBox',
  'dijit/layout/ContentPane',
  'dijit/layout/TabContainer',
  'codechecker/MessagePane',
  'codechecker/util',
  'products/PermissionList'],
function (declare, domAttr, domClass, domConstruct, Dialog, Button,
  NumberTextBox, RadioButton, SimpleTextarea, TextBox, ValidationTextBox,
  ContentPane, TabContainer, MessagePane, util, PermissionList) {

  /**
   * This dict sets for which database engine which configuration fields
   * should be visible.
   */
  var FIELD_SHOW_RULES = {
    null       : ['dbengine'],
    sqlite     : ['dbengine', 'dbname'],
    postgresql : ['dbengine', 'dbhost', 'dbport',
                  'dbuser', 'dbpass', 'dbname']
  };

  /**
   * This dict sets for which database engine, which field should have
   * customized values (such as placeholder and label text).
   *
   * Please make sure to fill the values accordingly, as the existence
   * and validity of a key for the given input element is NOT checked.
   *
   * Setting the values here for a field that is not marked as shown in
   * FIELD_SHOW_RULES is superfluous.
   */
  var FIELD_PRESENTATION_RULES = {
    null       : {},
    sqlite     : {
      dbname : {
        label       : "Database file",
        placeholder : "(If relative, to CONFIG_DIRECTORY)"
      }
    },
    postgresql : {
      dbname : {
        label       : "Database name",
        placeholder : "Database must exist!"
      }
    }
  };

  /**
   * This dict sets for which admin level which fields should be enabled.
   */
  var FIELD_RANK_SHOW_RULES = {
    0 : ['submit'],
    /* PRODUCT_ADMIN */ 1 : ['name', 'description'],
    /* SUPERUSER */     2 : ['endpoint', 'dbengine', 'dbhost', 'dbport',
                             'dbuser', 'dbpass', 'dbname', 'runlimit']
  };

  var ProductMetadataPane = declare(ContentPane, {
    constructor : function () {
      var that = this;

      this._mbox = new MessagePane({
        class   : 'mbox'
      });

      function setOrDeleteConfigValue() {
        if (this.value === "")
          that._deleteConfigValue(this.name);
        else
          that._setConfigValue(this.name, this.value);
      }

      //--- Product data ---//

      this._txtProdEndpoint = new ValidationTextBox({
        class       : 'form-input',
        name        : 'endpoint',
        placeholder : "Unique identifier for product!",
        required    : true,
        onChange    : setOrDeleteConfigValue
      });

      this._txtProdName = new TextBox({
        class       : 'form-input',
        name        : 'name',
        placeholder : '(Optional)',
        onChange    : setOrDeleteConfigValue
      });

      this._txtProdDescr = new SimpleTextarea({
        class       : 'form-input',
        name        : 'description',
        placeholder : '(Optional)',
        onChange    : setOrDeleteConfigValue
      });

      this._txtRunLimit = new NumberTextBox({
        class       : 'form-input',
        name        : 'run-limit',
        value       : null,
        constraints : {
          fractional : false,
          min        : 1
        },
        onChange : function () {
          that._setConfigValue('runlimit', this.value);
        }
      });

      //--- Database connection type buttons ---//

      this._btnSqlite = new RadioButton({
        name    : 'databaseEngine',
        value   : 'sqlite',
        onClick : function () {
          that._setDbEngine('sqlite');
        }
      });

      this._btnPostgres = new RadioButton({
        name    : 'databaseEngine',
        value   : 'postgresql',
        onClick : function () {
          that._setDbEngine('postgresql');
        }
      });

      //--- Database connection text boxes ---//

      this._txtDbHost = new TextBox({
        class    : 'form-input',
        name     : 'database/host',
        value    : 'localhost',
        onChange : setOrDeleteConfigValue
      });

      this._txtDbPort = new NumberTextBox({
        class       : 'form-input',
        name        : 'database/port',
        value       : 5432,
        constraints : {
          fractional : false,
          min        : 1,
          max        : 65535,
          pattern    : '####0'
        },
        onChange : function () {
          that._setConfigValue('database/port', this.value);
        }
      });

      this._txtDbUser = new TextBox({
        class       : 'form-input',
        name        : 'database/username',
        onChange    : setOrDeleteConfigValue
      });

      this._txtDbPass = new TextBox({
        class    : 'form-input',
        name     : 'database/password',
        type     : 'password',
        onChange : setOrDeleteConfigValue
      });

      this._txtDbName = new TextBox({
        class    : 'form-input',
        name     : 'database/name',
        onChange : setOrDeleteConfigValue
      });

      //--- Buttons ---//

      this._btnSubmit  = new Button({
        class   : 'submit-btn',
        label   : "Add",
        onClick : function () {
          that._mbox.hide();

          if (!that._validate())
            return;

          var product = that._createProductAPIObj();
          if (that.get('settingsMode') === 'add') {
            CC_PROD_SERVICE.addProduct(product, function(success) {
              if (success)
                  if (that.successCallback !== undefined)
                    that.successCallback(success);
            }).fail(function (jsReq, status, exc) {
              if (status === "parsererror")
                that._showMessageBox('error',
                  "Adding the product failed!", exc.message);
            });
          } else if (that.get('settingsMode') === 'edit') {
            CC_PROD_SERVICE.editProduct(that.productConfig['_id'], product,
              function(success) {
                if (success) {
                  if (that.successCallback !== undefined)
                    that.successCallback(success);

                  that._showMessageBox('success',
                    "Successfully edited the product settings!", "");
                }
            }).fail(function (jsReq, status, exc) {
              if (status === "parsererror")
                that._showMessageBox('error',
                  "Saving new settings failed!", exc.message);
            });
          }
        }
      });
    },

    /**
     * Convert the dialog's inner productConfig setting table into a
     * Thrift API ProductConfiguration object.
     */
    _createProductAPIObj : function () {
      var args = dojo.clone(this.productConfig);
      var engine = args['database/engine'];

      //--- Set default values to the configuration if user omits ---//
      // These rules are akin to that of the command-line client.
      if (!('database/name' in args)) {
        if (engine === 'sqlite') {
          args['database/name'] = args['endpoint'] + '.sqlite';
        } else if (engine === 'postgresql') {
          args['database/name'] = args['endpoint'];
        }
      }

      if (!('database/username' in args) && engine === 'postgresql')
        args['database/username'] = args['endpoint'];

      //--- Create the API descriptor structs for the new product ---//

      var dbConnection = new CC_PROD_OBJECTS.DatabaseConnection({
        engine: args['database/engine']
      });
      if (engine === 'sqlite') {
        dbConnection.host = "";
        dbConnection.port = 0;
        dbConnection.username_b64 = "";
        dbConnection.database = args['database/name'];
      } else if (engine === 'postgresql') {
        dbConnection.host = args['database/host'];
        dbConnection.port = args['database/port'];
        dbConnection.username_b64 = util.utoa(args['database/username']);
        if ('database/password' in args)
        // Database password isn't always a mandatory field.
          dbConnection.password_b64 = util.utoa(args['database/password']);
        dbConnection.database = args['database/name'];
      }

      var name = args['endpoint'];
      if ('name' in args) {
        name = args['name'];
      }

      var description = "";
      if ('description' in args) {
        description = args['description'];
      }

      var product = new CC_PROD_OBJECTS.ProductConfiguration({
        endpoint: args['endpoint'],
        runLimit: args['runlimit'] ? args['runlimit'] : null,
        displayedName_b64: util.utoa(name),
        description_b64: util.utoa(description),
        connection: dbConnection
      });

      return product;
    },

    _showMessageBox : function (mode, header, text) {
      domClass.toggle(this._mbox.domNode, "mbox-error", mode === 'error');
      domClass.toggle(this._mbox.domNode, "mbox-success", mode === 'success');
      this._mbox.show(header, text);
    },

    _placeFormElement : function (element, key, label) {
      var container = domConstruct.create('div', {
        class : 'formElement'
      }, this.containerNode);

      if (key)
        this._formElements[key] = {
          container : container,
          element   : element
        };

      if (label) {
        var labelNode = domConstruct.create('label', {
          class     : 'formLabel bold',
          innerHTML : label + ': '
        }, container);

        if (key) {
          domAttr.set(labelNode, 'for', key);
          this._formElements[key]['label'] = labelNode;
        }
      }

      domConstruct.place(element.domNode, container);
    },

    /**
     * Checks whether or not the form presented in the dialouge is valid.
     * It sets the submit button accordingly, and returns the result of
     * validation.
     */
    _validate : function () {
      var valid = false;

      if (this._formElements['endpoint']['element'].isValid() &&
          this._formElements['runlimit']['element'].isValid() &&
          'database/engine' in this.productConfig)
        valid = true;

      this._formElements['submit']['element'].setDisabled(!valid);

      return valid;
    },

    resetForm : function() {
      this._setDbEngine(null);
      this.set('settingsMode', null);
      this._txtDbPass.set('placeholder', '');
      this._btnSubmit.set('label', "Add");
      this.set('successCallback', undefined);
      this._resetProductConfig();
      this._btnSqlite.reset();
      this._btnPostgres.reset();

      for (var key in this._formElements) {
        if ('element' in this._formElements[key]) {
          if (typeof this._formElements[key]['element'].reset === "function")
            this._formElements[key]['element'].reset();

          this._formElements[key]['element'].set('disabled', false);
        }
      }
      this._mbox.hide();
    },

    _setDbEngine : function (engine) {
      if (engine !== null)
        this._setConfigValue('database/engine', engine);
      else
        this._deleteConfigValue('database/engine');

      for (var key in this._formElements) {
        if (key.indexOf('db') === 0) {
          // Show the database configuration option based on the engine.
          // If engine is null, it will hide everything. Otherwise, it will
          // automatically hide the fields that are not marked to show.
          var show = FIELD_SHOW_RULES[engine].indexOf(key) > -1;
          domClass.toggle(this._formElements[key]['container'], 'hide', !show);

          if (key in FIELD_PRESENTATION_RULES[engine]) {
            var rule = FIELD_PRESENTATION_RULES[engine][key];

            for (var ruleKey in rule) {
              if (ruleKey === 'label') {
                this._formElements[key]['label'].innerHTML =
                  rule[ruleKey] + ': ';
              } else {
                this._formElements[key]['element'].set(
                  ruleKey, rule[ruleKey]);
              }
            }
          }
        }
      }
    },

    _setConfigValue : function (key, value) {
      this.productConfig[key] = value;
      this._validate();
    },

    _deleteConfigValue : function (key) {
      if (key in this.productConfig) {
        delete this.productConfig[key];
        this._validate();
      }
    },

    _resetProductConfig : function () {
      // Set the internal configuration array to the default values of the
      // dialog form.
      this.set('productConfig', {
        'database/host' : 'localhost',
        'database/port' : 5432
      });
    },

    /**
     * Set the dialog's form elements values retrieved from the API.
     *
     * @param {ProductService.ProductConfiguration} productAPIObj The API
     *   result object.
     */
    setProductConfig : function (productAPIObj) {
      this._btnSubmit.set('label', "Save");
      this._txtDbPass.set('placeholder', "(Won't be changed.)");

      var that = this;
      var setCfg = function (element, key, value) {
        that._setConfigValue(key, value);
        element.set('value', value);
      };

      this._setConfigValue('_id', productAPIObj.id);

      setCfg(this._txtProdEndpoint, 'endpoint', productAPIObj.endpoint);
      setCfg(this._txtRunLimit, 'runlimit', productAPIObj.runLimit);
      setCfg(this._txtProdName, 'name',
             util.atou(productAPIObj.displayedName_b64));

      if (productAPIObj.description_b64)
        setCfg(this._txtProdDescr, 'description',
               util.atou(productAPIObj.description_b64));

      var connection = productAPIObj.connection;
      this._setDbEngine(connection.engine);
      if (connection.engine === 'sqlite') {
        this._btnSqlite.set('checked', true);

        setCfg(this._txtDbName, 'database/name', connection.database);
      } else if (productAPIObj.connection.engine === 'postgresql') {
        this._btnPostgres.set('checked', true);

        setCfg(this._txtDbHost, 'database/host', connection.host);
        setCfg(this._txtDbPort, 'database/port', connection.port);
        setCfg(this._txtDbUser, 'database/username',
               util.atou(connection.username_b64));
        setCfg(this._txtDbName, 'database/name', connection.database);
        // The password field defaults to "not changed" as we are NOT
        // showing the password.
      }

      this._validate();
    },

    /**
     * Set the editable fields on the form based on the admin level of the
     * user.
     */
    setAdminLevel : function (adminLevel) {
      var that = this;

      this._btnSqlite.set('disabled', adminLevel < 2);
      this._btnPostgres.set('disabled', adminLevel < 2);

      function shouldEnable(key) {
        for (var i = 0; i <= adminLevel; ++i)
          if (FIELD_RANK_SHOW_RULES[i].indexOf(key) !== -1)
            return true;

        return false;
      }

      for (var key in this._formElements) {
        domClass.toggle(this._formElements[key]['container'], 'invisible',
          !shouldEnable(key));

        if (this._formElements[key]['element'])
          this._formElements[key]['element'].set(
            'disabled', !shouldEnable(key));
      }
    },

    postCreate : function () {
      this.inherited(arguments);

      this._resetProductConfig();
      this.set('_formElements', {});

      this.addChild(this._mbox);
      this._mbox.hide();

      //--- Set up the form ---//

      this._placeFormElement(this._txtProdEndpoint, 'endpoint',
                             "URL endpoint");
      this._placeFormElement(this._txtProdName, 'name', "Display name");
      this._placeFormElement(this._txtProdDescr, 'description', "Description");
      this._placeFormElement(this._txtRunLimit, 'runlimit', "Run limit");

      //--- The database configuration selector is special ---//

      domConstruct.create('hr', null, this.containerNode);
      var dbEngineContainer = domConstruct.create('div', {
        class : 'formElement'
      }, this.containerNode);
      this._formElements['dbengine'] = {
        container : dbEngineContainer
      };

      domConstruct.create('span', {
        class     : 'formLabel bold',
        innerHTML : "Database engine:"
      }, dbEngineContainer);

      var dbSqlite = domConstruct.create('div', {
        class : 'formElement'
      }, dbEngineContainer);
      domConstruct.place(this._btnSqlite.domNode, dbSqlite);
      domConstruct.create('label', {
        class     : 'formLabel',
        innerHTML : "SQLite"
      }, dbSqlite);

      // TODO: PostgreSQL show only if server supports it!
      var dbPostgres = domConstruct.create('div', {
        class : 'formElement'
      }, dbEngineContainer);
      domConstruct.place(this._btnPostgres.domNode, dbPostgres);
      domConstruct.create('label', {
        class     : 'formLabel',
        innerHTML : "PostgreSQL"
      }, dbPostgres);

      //--- Put the rest of the form elements onto the view. ---//

      this._placeFormElement(this._txtDbHost, 'dbhost', "Server address");
      this._placeFormElement(this._txtDbPort, 'dbport', "Port");
      this._placeFormElement(this._txtDbUser, 'dbuser', "Username");
      this._placeFormElement(this._txtDbPass, 'dbpass', "Password");
      this._placeFormElement(this._txtDbName, 'dbname', "DATABASE_NAME");

      this._placeFormElement(this._btnSubmit, 'submit');

      // By default, don't show the database fine-tuning options.
      this._setDbEngine(null);
      this._validate();
    }
  });

  var ProductPermissionsPane = declare(ContentPane, {
    constructor : function () {
      var that = this;

      this.permissionView = new PermissionList();

      this._mbox = new MessagePane({
        class   : 'mbox'
      });

      this._btnSave  = new Button({
        class   : 'submit-btn',
        label   : "Save",
        onClick : function () {
          that._mbox.hide();

          var errors = [];
          var permDiff = that.permissionView.getPermissionDifference();
          var extraParams = that.permissionView.get('extraParamsJSON');
          permDiff.forEach(function (record) {
           try {
              if (record.action === 'ADD')
                CC_AUTH_SERVICE.addPermission(
                  record.permission, record.name, record.isGroup, extraParams);
              else if (record.action === 'REMOVE')
                CC_AUTH_SERVICE.removePermission(
                  record.permission, record.name, record.isGroup, extraParams);
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
              text += '<li><strong>' + (record.action === 'ADD'
                                        ? "Add" : "Remove") +
                      '</strong> permission <strong>' + permissionName +
                      '</strong> of ' + (record.isGroup ? "group" : "user") +
                      ' <strong>' + record.name + '</strong>.</li>\n';
            });
            text += '</ul>';


            that._showMessageBox(
              'error',
              "Some permission changes could not be saved",
              text);
          } else {
            that._showMessageBox(
              'success',
              "Permission changes saved successfully!",
              "");

            if (that.successCallback !== undefined)
              that.successCallback();
          }
        }
      });
    },

    _showMessageBox : function (mode, header, text) {
      domClass.toggle(this._mbox.domNode, "mbox-error", mode === 'error');
      domClass.toggle(this._mbox.domNode, "mbox-success", mode === 'success');
      this._mbox.show(header, text);
    },

    populatePermissions : function(productID) {
      this._mbox.hide();

      this.permissionView.populatePermissions('PRODUCT', {
        productID : productID
      });
    },

    postCreate : function () {
      this.inherited(arguments);

      this.addChild(this._mbox);
      this._mbox.hide();

      this.addChild(this.permissionView);
      this.addChild(this._btnSave);
    }
  });

  return declare(Dialog, {
    constructor : function () {
      this._tabWrapper = new ContentPane({
        style : 'width: 650px; height: 450px'
      });

      this._tabView = new TabContainer();

      this._metadataPane = new ProductMetadataPane({
        title    : "Product settings",
        closable : false
      });

      this._permissionPane = new ProductPermissionsPane({
        title    : "Permissions",
        closable : false
      });
    },

    postCreate : function () {
      this.inherited(arguments);

      this._tabView.addChild(this._metadataPane);
      this._tabView.addChild(this._permissionPane);

      this._tabWrapper.addChild(this._tabView);
      this.addChild(this._tabWrapper);
    },

    onHide : function () {
      this._metadataPane.resetForm();
    },

    setMode : function (adminLevel, mode, productID, successCallback) {
      this._tabView.selectChild(this._metadataPane);

      this._metadataPane.setAdminLevel(adminLevel);
      this._metadataPane.set('successCallback', successCallback);
      this._permissionPane.set('successCallback', successCallback);

      if (mode === 'add') {
        this.set('title', "Add new product");
        this._metadataPane.set('settingsMode', 'add');
        this._permissionPane.set('disabled', true);
      } else if (mode === 'edit') {
        var configuration = CC_PROD_SERVICE.getProductConfiguration(productID);
        this.set(
          'title', "Edit product '" + configuration.endpoint + "'");
        this._metadataPane.setProductConfig(configuration);
        this._metadataPane.set('settingsMode', 'edit');
        this._permissionPane.set('disabled', false);
        this._permissionPane.populatePermissions(productID);
      }
    }
  });
});
