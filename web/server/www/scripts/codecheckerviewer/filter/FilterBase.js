// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
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
