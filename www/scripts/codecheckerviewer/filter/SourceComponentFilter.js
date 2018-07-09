// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter'],
function (declare, dom, Deferred, SelectFilter) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      placeHolder : 'Search for source components...'
    },

    formatDescription : function (value) {
      var list = dom.create('ul', { class : 'component-description'});
      value.split('\n').forEach(function (item) {
        dom.create('li', {
          innerHTML : item,
          class : 'component-item'
        }, list);
      });
      return list.outerHTML;
    },

    getItems : function () {
      var that = this;

      var deferred = new Deferred();
      CC_SERVICE.getSourceComponents(null, function (res) {
        deferred.resolve(res.map(function (component) {
          return {
            value : component.name,
            description : that.formatDescription(component.value)
          };
        }));
      });
      return deferred;
    }
  });
});
