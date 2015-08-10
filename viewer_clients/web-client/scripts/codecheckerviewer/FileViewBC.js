// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/dom-construct",
  "dijit/layout/ContentPane",
  "dijit/layout/BorderContainer",
  "dijit/Dialog",
  "dijit/form/Button",
  "dijit/form/Textarea",
  "scripts/codecheckerviewer/BugStMoTr.js",
  "scripts/codecheckerviewer/Editor.js",
  "scripts/codecheckerviewer/widgets/EditorHeader.js",
], function ( declare, domConstruct, ContentPane, BorderContainer, Dialog
            , Button, Textarea, BugStMoTr, Editor, EditorHeader ) {
return declare(BorderContainer, {

  // fileId
  // checkedFile
  // bugHash
  // severity
  // lastBugPosition
  // reportId
  // myOverviewTC
  // currCheckerId
  // suppressed
  // runId


  constructor : function(args) {
    var that = this;
    declare.safeMixin(that, args);
  },


  postCreate : function () {
    var that = this;
    that.inherited(arguments);


    var fileId          = that.fileId;
    var checkedFile     = that.checkedFile;
    var bugHash         = that.bugHash;
    var severity        = that.severity;
    var lastBugPosition = that.lastBugPosition;
    var reportId        = that.reportId;
    var myOverviewTC    = that.myOverviewTC;
    var currCheckerId   = that.currCheckerId;
    var suppressed      = that.suppressed;
    var runId           = that.runId;

    that.viewedFile   = checkedFile;
    that.viewedFileId = fileId;

    that.title         = checkedFile.split(/[\/]+/).pop() + " @ Line " + lastBugPosition.startLine;
    that.liveSplitters = false;
    that.closable      = true;
    that.onClose       = function() {
      if (myOverviewTC.selectedChildWidget === that) {
        myOverviewTC.selectChild(myOverviewTC.overviewBC.id);
      }

      return true;
    };


    var editorBC = new BorderContainer({
      region : "center",
      style  : "padding: 0px;"
    });


    var editorHeaderCP = new ContentPane({
      region : "top",
      style  : "padding: 0px;"
    });

    var editorHeader = new EditorHeader();


    var editorCP = new ContentPane({
      region : "center",
      style  : "padding: 0px;"
    }, domConstruct.create("div"));

    var editor = new Editor({
      editorCP : editorCP
    }, domConstruct.create("div"));


    var treePane = new ContentPane({
      region   : "left",
      splitter : true,
      style    : "padding: 0px; width: 25%;"
    });

    that.bugStMoTr = new BugStMoTr({
      fileId          : fileId,
      filePath        : checkedFile,
      reportDataStore : myOverviewTC.overviewGrid.store
    });

    that.bugStMoTr.bugTree.onClick = function(item) {
      if (item.isLeaf === true) {

        if (that.viewedFile !== item.filePath) {
          that.viewedFile   = item.filePath;
          that.viewedFileId = item.fileId;

          editor._setContentAttr(CC_SERVICE.getSourceFileData(item.fileId, true).fileContent);
          editor.setFileName(that.viewedFile.split("/").pop());
          editor.setPath(that.viewedFile);
        }

        var newRange = that.createRangeFromBugPos(item.range);
        that.jumpToRangeAndDrawBubblesLines(editor, newRange, item.reportId);

        that.currCheckerId = item.checkerId;
        that.reportId = item.reportId;

        that.set("title", checkedFile.split(/[\/]+/).pop() + " @ Line " + item.range.startLine);

        if (item.suppressed === false) {
          editorHeader.suppressButton.setDisabled(false);
        }

      }
    };


    editorHeader.documentationButton.onClick = function() {
      myOverviewTC.showDocumentation(that.currCheckerId);
    };


    editorHeader.suppressButton.onClick = function() {
      var suppressDialog = new Dialog({
        title : "Comment for the suppress",
        style : "text-align: center;"
      });

      var suppressTextarea = new Textarea({
        maxLength : 1024
      });

      var sendSuppressButton = new Button({
        label   : "Suppress",
        onClick : function() {
          try {

            sendSuppressButton.setDisabled(true);
            CC_SERVICE.suppressBug([runId], that.reportId, suppressTextarea.getValue());

            CCV.reset();

            myOverviewTC.overviewGrid.refreshGrid();

            that.bugStMoTr.bugStore.remove(that.bugStMoTr.bugTree.selectedItem.parent);

            that.clearSelectionAndBubblesLines(editor);

            editorHeader.suppressButton.setDisabled(true);

          } catch (err) {
            console.log(err);

            var errorDialog = new Dialog({
              title   : "Error",
              content : "Failed to suppress bug."
            });

            errorDialog.show();
          }

          suppressDialog.hide();

        }
      });

      suppressDialog.addChild(suppressTextarea);
      suppressDialog.addChild(sendSuppressButton);

      suppressDialog.show();
    };


    if (suppressed === true) {
      editorHeader.suppressButton.setDisabled(true);
    }


    that.bugStMoTr.bugTree.set("path", ["root", severity, bugHash]);
    setTimeout(function(){ that.bugStMoTr.bugTree.set("path", ["root", severity, bugHash, bugHash + "_0"]); }, 0);

    editor._setContentAttr(CC_SERVICE.getSourceFileData(fileId, true).fileContent);
    editor.setFileName(that.viewedFile.split("/").pop());
    editor.setPath(that.viewedFile);


    var newRange = that.createRangeFromBugPos(lastBugPosition);
    that.jumpToRangeAndDrawBubblesLines(editor, newRange, reportId);


    treePane.addChild(that.bugStMoTr.bugTree);
    editorCP.addChild(editor);
    editorHeaderCP.addChild(editorHeader);

    editorBC.addChild(editorCP);
    editorBC.addChild(editorHeaderCP);

    that.addChild(treePane);
    that.addChild(editorBC);

  },


  jumpToRangeAndDrawBubblesLines : function(editor, range, reportId) {
    var that = this;


    editor.clearBubbles();
    editor.clearLines();


    var reportDetails = CC_SERVICE.getReportDetails(reportId);

    var filterFunction = function(obj) {
      if (obj.fileId === that.viewedFileId) {
        return true;
      } else {
        return false;
      }
    }

    var allPoints = reportDetails.executionPath;

    that.createAndAddFileJumpBubbles(allPoints, editor);

    var points  = allPoints.filter(filterFunction);
    var bubbles = reportDetails.pathEvents.filter(filterFunction);

    // This is needed because CodeChecker gives different positions.
    points.forEach(function (point)   { --point.startCol;  });
    bubbles.forEach(function (bubble) { --bubble.startCol; });

    editor.addBubbles(bubbles);
    editor.addLines(points);


    var fln = editor.codeMirror.options.firstLineNumber;
    var newPoint = editor.codeMirror.doc.markText(
      { line : range.from.line - fln, ch : range.from.column - 1 },
      { line : range.to.line   - fln, ch : range.to.column - 1   },
      { className : "codemirrorselection" });
    editor._lineMarks.push(newPoint);

    editor.jumpTo(range.from.line, range.from.column);
  },


  clearSelectionAndBubblesLines : function(editor) {
    var that = this;


    var noRange = that.createRangeFromBugPos({
      startLine : 0,
      endLine   : 0,
      startCol  : 0,
      endCol    : 0
    });

    editor._setSelectionAttr(noRange);
    editor.clearBubbles();
    editor.clearLines();

  },


  createRangeFromBugPos : function(bugPosition) {
    return {
      from : { line : bugPosition.startLine , column : bugPosition.startCol   },
      to   : { line : bugPosition.endLine   , column : bugPosition.endCol + 1 }
    }

  },


  createAndAddFileJumpBubbles : function(points, editor) {
    var that = this;


    var bubbleInfoArray = [];
    var lastStartLine = null;
    var swtch = false;

    for (var i = 0 ; i < points.length ; ++i) {

      var areFilesTheSame = points[i].fileId === that.viewedFileId;

      if (swtch && !areFilesTheSame) {
        bubbleInfoArray.push({
          filePath   : points[i].filePath,
          fileId     : points[i].fileId,
          line       : lastStartLine-1,
          fileViewBC : that
        });

        swtch = false;
      } else if (swtch && areFilesTheSame) {
        lastStartLine  = points[i].startLine;
        lastStartPoint = points[i];
      } else if (!swtch && areFilesTheSame) {
        --i;
        swtch = true;
      }

    }

    for (var i = 0 ; i < bubbleInfoArray.length ; ++i) {
      editor.addNewOtherFileBubble(
        bubbleInfoArray[i].filePath,
        bubbleInfoArray[i].fileId,
        bubbleInfoArray[i].line,
        bubbleInfoArray[i].fileViewBC
      );
    }
  }


});});
