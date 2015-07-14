// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/store/Memory",
  "dojo/store/Observable",
  "dijit/tree/ObjectStoreModel",
  "dijit/Tree",
  "dijit/Tooltip"
], function ( declare, Memory, Observable, ObjectStoreModel, Tree, Tooltip ) {
return declare(null, {

  // fileId
  // filePath
  // reportDataStore


  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);

    that.createBugStoreData(that.fileId, that.filePath);


    that.bugStore = new Observable(new Memory({
      data        : that.bugStoreData,
      getChildren : function(node) {
        return this.query({ parent: node.id });
      }
    }));


    that.bugModel = new ObjectStoreModel({
      store : that.bugStore,
      query : { id : "root" },
      mayHaveChildren: function(item){
        return (item.isLeaf === false);
      }
    });


    that.bugTree = new Tree({
      region       : "left",
      splitter     : true,
      model        : that.bugModel,
      openOnClick  : true,
      showRoot     : false,
      getIconClass : function(item, opened) {
        if (item.isLeaf === false) {
          if (opened) {
            return "dijitFolderOpened";
          } else {
            return "dijitFolderClosed";
          }
        } else {
          return "dijitLeaf";
        }
      },
      _onNodeMouseEnter : function(node, evt) {
        if (node.item.isLeaf === true) {
          Tooltip.show(node.item.name, node.domNode, ['above']);
        }
      },
      _onNodeMouseLeave : function(node, evt) {
        if (node.item.isLeaf === true) {
          Tooltip.hide(node.domNode);
        }
      }
    });

  },


  createBugStoreData : function(fileId, filePath) {
    var that = this;

    var bugStoreDataTmp = [
      {
        name : "Bugs by priority",
        id   : "root"
      },{
        name   : "Critical",
        id     : "critical",
        parent : "root",
        isLeaf : false
      },{
        name   : "High",
        id     : "high",
        parent : "root",
        isLeaf : false
      },{
        name   : "Medium",
        id     : "medium",
        parent : "root",
        isLeaf : false
      },{
        name   : "Low",
        id     : "low",
        parent : "root",
        isLeaf : false
      },{
        name   : "Style",
        id     : "style",
        parent : "root",
        isLeaf : false
      },{
        name   : "Unspecified",
        id     : "unspecified",
        parent : "root",
        isLeaf : false
      }
    ];


    var storeAsArray = that.reportDataStore._arrayOfAllItems;

    for (var i = 0 ; i < storeAsArray.length ; ++i) {

      var item = storeAsArray[i];

      if (item.fileId[0] === fileId) {
        bugStoreDataTmp.push({
          name       : "Line " + item.lastBugPosition[0].startLine + " : " + item.checkerId[0],
          id         : item.bugHash[0],
          parent     : item.severity[0],
          range      : item.lastBugPosition[0],
          reportId   : item.reportId[0],
          checkerId  : item.checkerId[0],
          suppressed : item.suppressed[0],
          isLeaf     : false
        });

        bugStoreDataTmp.push({
          name       : "Line " + item.lastBugPosition[0].startLine + " : " + item.checkerMsg[0],
          id         : item.bugHash[0] + "_0",
          parent     : item.bugHash[0],
          range      : item.lastBugPosition[0],
          filePath   : filePath,
          fileId     : item.fileId[0],
          reportId   : item.reportId[0],
          checkerId  : item.checkerId[0],
          suppressed : item.suppressed[0],
          isLeaf     : true
        });

        var execPath = CC_SERVICE.getReportDetails(item.reportId[0]).executionPath;

        for (var j = 0 ; j < execPath.length ; ++j) {

          bugStoreDataTmp.push({
            name       : "Step " + (j + 1) + " : " + execPath[j].filePath.split("/").pop() + " : Line " + execPath[j].startLine,
            id         : item.bugHash[0] + "_" + (j + 1),
            parent     : item.bugHash[0],
            range      : execPath[j],
            filePath   : execPath[j].filePath,
            fileId     : execPath[j].fileId,
            reportId   : item.reportId[0],
            checkerId  : item.checkerId[0],
            suppressed : item.suppressed[0],
            isLeaf     : true
          });

        }

      }

    }

    that.bugStoreData = bugStoreDataTmp;
  }


});});
