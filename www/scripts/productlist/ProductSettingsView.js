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
  'codechecker/MessagePane',
  'codechecker/util'],
function (declare, domAttr, domClass, domConstruct, Dialog, Button,
  NumberTextBox, RadioButton, SimpleTextarea, TextBox, ValidationTextBox,
  ContentPane, MessagePane, util) {

  return declare(Dialog, {
    constructor : function () {
      var that = this;

      this._error = new MessagePane({
        class   : 'mbox mbox-error'
      });

      //--- Product data ---//

      this._txtProdEndpoint = new ValidationTextBox({
        class       : 'formInput',
        name        : 'endpoint',
        placeholder : "Unique identifier for product!",
        required    : true,
        onChange : function () {
          if (this.value === "")
            that._deleteConfigValue('endpoint');
          else
            that._setConfigValue('endpoint', this.value);
        }
      });

      this._txtProdName = new TextBox({
        class       : 'formInput',
        name        : 'name',
        placeholder : '(Optional)',
        onChange : function () {
          if (this.value === "")
            that._deleteConfigValue('name');
          else
            that._setConfigValue('name', this.value);
        }
      });

      this._txtProdDescr = new SimpleTextarea({
        class       : 'formInput',
        name        : 'description',
        placeholder : '(Optional)',
        onChange : function () {
          if (this.value === "")
            that._deleteConfigValue('description');
          else
            that._setConfigValue('description', this.value);
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
        class    : 'formInput',
        name     : 'dbhost',
        value    : 'localhost',
        onChange : function () {
          if (this.value === "")
            that._deleteConfigValue('database/host');
          else
            that._setConfigValue('database/host', this.value);
        }
      });

      this._txtDbPort = new NumberTextBox({
        class       : 'formInput',
        name        : 'dbport',
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
        class       : 'formInput',
        name        : 'dbuser',
        onChange    : function () {
          if (this.value === "")
            that._deleteConfigValue('database/username');
          else
            that._setConfigValue('database/username', this.value);
        }
      });

      this._txtDbPass = new TextBox({
        class    : 'formInput',
        name     : 'dbport',
        type     : 'password',
        onChange : function () {
          if (this.value === "")
            that._deleteConfigValue('database/password');
          else
            that._setConfigValue('database/password', this.value);
        }
      });

      this._txtDbName = new TextBox({
        class    : 'formInput',
        name     : 'dbname',
        onChange : function () {
          if (this.value === "")
            that._deleteConfigValue('database/name');
          else
            that._setConfigValue('database/name', this.value);
        }
      });

      //--- Buttons ---//
      this._btnSubmit  = new Button({
        class   : 'submit-btn',
        label   : "Add",
        onClick : function () {
          that._hideError();

          if (!that._validate())
            return;

          // TODO: Check if user is superuser before calling the API.
          var product = that._createProductAPIObj();
          if (that.get('settingsMode') === 'add') {
            util.asyncAPICallWithExceptionHandling(
              PROD_SERVICE,
              'addProduct',
              product,
              function (success) {
                if (success) {
                  that.hide();
                  if (that.successCallback !== undefined)
                    that.successCallback(success);
                  that._resetDialog();
                }
              },
              function (exc) {
                that._showError("Adding the product failed!", exc.message);
              }
            )
          } else if (that.get('settingsMode') === 'edit') {
            util.asyncAPICallWithExceptionHandling(
              PROD_SERVICE,
              'editProduct',
              that.productConfig['_id'],
              product,
              function (success) {
                if (success) {
                  that.hide();
                  if (that.successCallback !== undefined)
                    that.successCallback(success);
                  that._resetDialog();
                }
              },
              function (exc) {
                console.log(exc);
                that._showError("Saving new settings failed!", exc.message);
              }
            )
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
        displayedName_b64: util.utoa(name),
        description_b64: util.utoa(description),
        connection: dbConnection
      });

      return product;
    },

    /**
     * This dict sets for which database engine which configuration fields
     * should be visible.
     */
    FIELD_SHOW_RULES : {
      null       : [],
      sqlite     : ['dbname'],
      postgresql : ['dbhost', 'dbport', 'dbuser', 'dbpass', 'dbname']
    },

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
    FIELD_PRESENTATION_RULES : {
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
    },

    _showError : function (header, errorMsg) {
      this._error.show(header, errorMsg);
    },

    _hideError : function () {
      this._error.hide();
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
        });

        if (key) {
          domAttr.set(labelNode, 'for', key);
          this._formElements[key]['label'] = labelNode;
        }

        domConstruct.place(labelNode, container);
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
          'database/engine' in this.productConfig)
        valid = true;

      this._formElements['submit']['element'].setDisabled(!valid);

      return valid;
    },

    _resetDialog : function() {
      this._setDbEngine(null);
      this.set('title', '');
      this.set('settingsMode', null);
      this._txtDbPass.set('placeholder', '');
      this._btnSubmit.set('label', "Add");
      this.set('successCallback', undefined);
      this._resetProductConfig();
      this._btnSqlite.reset();
      this._btnPostgres.reset();

      for (var key in this._formElements)
        if (typeof this._formElements[key]['element'].reset === "function")
          this._formElements[key]['element'].reset();
      this._hideError();
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
          var show = this.FIELD_SHOW_RULES[engine].indexOf(key) > -1;
          domClass.toggle(this._formElements[key]['container'], 'hide', !show);

          if (key in this.FIELD_PRESENTATION_RULES[engine]) {
            var rule = this.FIELD_PRESENTATION_RULES[engine][key];

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

    onCancel : function () {
      this._resetDialog();
    },

    postCreate : function () {
      this.inherited(arguments);

      this._resetProductConfig();
      this.set('_formElements', {});

      this.addChild(this._error);
      this._hideError();

      //--- Set up the form ---//

      this._placeFormElement(this._txtProdEndpoint, 'endpoint',
                             "URL endpoint");
      this._placeFormElement(this._txtProdName, 'name', "Display name");
      this._placeFormElement(this._txtProdDescr, 'description', "Description");

      //--- The database configuration selector is special ---//

      domConstruct.create('hr', null, this.containerNode);
      var dbEngineContainer = domConstruct.create('div', {
        class : 'formElement'
      }, this.containerNode);

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
});
