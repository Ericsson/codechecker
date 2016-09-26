// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dijit/form/TextBox',
  'dijit/form/Select',
  'dijit/layout/ContentPane',
  'codechecker/util'],
function (domConstruct, declare, TextBox, Select, ContentPane, util) {
  return declare(ContentPane, {
    constructor : function () {
      this.fields = [];
      this._previousValues = {};
      this.style = 'padding: 0;';
    },

    /**
     * By this function one can add a new input field to the filter.
     * @param {String} type This parameter determines the type of the field
     * which can be 'text' or 'select'.
     * @param {Array|Function|String} content This parameter contains the
     * content of the input field. In case of 'text' type the content should be
     * a string which appears as a place holder in the field. In case of select
     * the content should be an array of { label : ..., value : ... } objects or
     * a function returning such an array. 
     */
    addField : function (type, name, content) {
      var that = this;

      switch (type) {
        case 'text':
          var field = new TextBox({
            placeHolder : content,
            name : name,
            class : 'filterText',
            onKeyPress : function (evt) {
              if (!that._changeHappened()) return;

              if (evt.keyCode === 13) { // "Enter"
                that.onChange(that.getValues());
                that._updateContent(field);
              }
            }
          });
          break;

        case 'select':
          var field = new Select({
            forceWidth : true,
            name : name,
            class : 'filterSelect',
            onChange : function () {
              if (field.get('value') === '_loading_' || !that._changeHappened())
                return;

              that.onChange(that.getValues());
              that._updateContent(field);
            }
          });

          if (typeof content === 'function') {
            field.contentCallback = content;
            that._replaceOptions(field);
          } else {
            field.set('options', content);
            field.reset();
            that._previousValues[field.get('name')] = field.get('value');
          }

          break;

        default:
          return;
      }

      this._previousValues[field.get('name')] = field.get('value');
      this.fields.push(field);
      this.addChild(field);
    },

    /**
     * This function returns the value of the fields with the given name.
     */
    getValue : function (name) {
      var field = util.findInArray(this.fields, function (field) {
        return field.get('name') === name;
      });

      if (field)
        return field.get('value');
    },

    /**
     * This function returns an object of which the keys are the names of the
     * fields and the values are the values of the fields.
     */
    getValues : function () {
      var result = {};

      this.fields.forEach(function (field) {
        result[field.get('name')] = field.get('value');
      });

      return result;
    },

    setDisabledAll : function (disabled) {
      this.fields.forEach(function (field) {
        field.set('disabled', disabled);
      });
    },

    /**
     * Select type fields can be given a callback function to determine their
     * values. By calling this function the callback function will be invoked to
     * update the values.
     */
    _updateContent : function (changedField) {
      var that = this;

      this.fields.forEach(function (field) {
        if (field !== changedField && field.contentCallback) {
          that._replaceOptions(field);
        }
      });
    },

    _replaceOptions : function (select) {
      var that = this;

      select.set('options', [{ label : 'Loading...', value : '_loading_' }]);
      select.set('disabled', true);
      this.setDisabledAll(true);
      select.reset();

      select.contentCallback(function (opts) {
        select.set('options', opts);
        select.set('disabled', false);
        that.setDisabledAll(false);
        select.reset();
        that._previousValues[select.get('name')] = select.get('value');
      });
    },

    _changeHappened : function () {
      var currentValues = this.getValues();

      for (var key in this._previousValues)
        if (currentValues[key] !== this._previousValues[key]) {
          this._previousValues = currentValues;
          return true;
        }

      return false;
    },

    /**
     * This event is emitted if a field value changes. The callback function is
     * given an object which contains the field values.
     */
    onChange : function (values) {
    }
  });
});
