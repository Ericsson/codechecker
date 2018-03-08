// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dijit/layout/ContentPane'],
function (declare, dom, ContentPane) {
  return declare(ContentPane, {
    postCreate : function () {
      this.inherited(arguments);

      if (!this.options) this.options = {};

      if (this.iconClass)
        dom.create('span', {
          class : this.iconClass,
          style: this.iconStyle
        }, this.domNode);

      this._labelWrapper = dom.create('span', {
        class : 'label',
        title : this.label,
        innerHTML : this.label
      }, this.domNode);

      if (!this.options.disableCount)
        this._countWrapper = dom.create('span', {
          class : 'count',
          innerHTML : this.options.count === undefined
                    ? 'N/A'
                    : this.options.count
        }, this.domNode);

      if (!this.options.disableRemove)
        dom.create('span', {
          class : 'customIcon remove'
        }, this.domNode);
    },

    // Update selected filter item by the options parameter.
    update : function (options) {
      if (this._countWrapper) {
        this.options.count = options ? options.count : null;
        this._countWrapper.innerHTML = options && options.count !== undefined
          ? options.count
          : 'N/A';
      }
    }
  });
});
