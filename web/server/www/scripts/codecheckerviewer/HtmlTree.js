// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
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
