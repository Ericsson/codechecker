// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dijit/_WidgetBase',
  'dojo/_base/declare'],
function (_WidgetBase, declare) {
  return declare(_WidgetBase, {
    // Initalize filter state by URL values.
    initByUrl : function (queryParams) {},

    // Clears out the filter state.
    clear : function () {},

    // Being notified from filter change events.
    notify : function () {},

    // Get URL query parameters.
    getUrlState : function () { return {}; }
  });
});
