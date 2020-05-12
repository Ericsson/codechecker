// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dijit/Tree'],
function (declare, Tree) {
  var HtmlTreeNode = declare(Tree._TreeNode, {
    _setLabelAttr : { node : 'labelNode', type : 'innerHTML' },
    _setIndentAttr : function (indent) {
      if (this.item.indent) {
        indent = this.item.indent;
      }

      this.inherited(arguments);
    }
  });

  return declare(Tree, {
    _createTreeNode : function (args) {
      var node = new HtmlTreeNode(args);

      if (args.item.backgroundColor) {
        node.domNode.style.backgroundColor = args.item.backgroundColor;
      }

      return node;
    }
  });
});
