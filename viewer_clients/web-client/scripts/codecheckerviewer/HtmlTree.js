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
    _setLabelAttr : { node : 'labelNode', type : 'innerHTML' }
  });

  return declare(Tree, {
    _createTreeNode : function (args) {
      node = new HtmlTreeNode(args);

      if (args.item.backgroundColor) {
        node.domNode.style.backgroundColor = args.item.backgroundColor;
      }

      return node;
    }
  });
});
