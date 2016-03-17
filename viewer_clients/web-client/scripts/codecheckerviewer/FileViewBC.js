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
  "ccvscripts/BugStoreModelTree",
  "ccvscripts/Editor",
  "ccvscripts/widgets/EditorHeader",
], function (declare, domConstruct, ContentPane, BorderContainer, Dialog,
  Button, Textarea, BugStoreModelTree, Editor, EditorHeader) {
return declare(BorderContainer, {

  /**
   * Construct the new object. The following arguments are required:
   *   fileId: the id of the file
   *   checkedFile: the filename (path) of the file
   *   bugHash: the hash of the bug
   *   severity: the severity of the bug
   *   lastBugPosition: the position of the last step in the bug step chain
   *   reportId: the id of the report
   *   myOverviewTC: the id of the OverviewTC to which this FileViewBC belongs
   *   currCheckerId: the checker id of currently selected bug
   *   suppressed: whether the bug is suppressed or not
   *   runId: the runId of the run in which the bug is found
   */
  constructor : function (args) {
    var that = this;
    declare.safeMixin(that, args);
  },

  /**
   * Creation of the layout of the FileView, creation of its widgets, placement
   * of event listeners happen here.
   */
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
    that.onClose       = function () {
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

    that.bugStoreModelTree = new BugStoreModelTree({
      runId           : runId,
      fileId          : fileId,
      filePath        : checkedFile,
      onLoaded        : function () {
        that.bugStoreModelTree.bugTree.set("path", ["root", severity, bugHash,
          bugHash + "_0"]);
      }
    });

    that.bugStoreModelTree.bugTree.onClick = function (item) {
      if (item.isLeaf === true) {

        if (that.viewedFile !== item.filePath) {
          that.viewedFile   = item.filePath;
          that.viewedFileId = item.fileId;

          CC_SERVICE.getSourceFileData(that.viewedFileId, true, function (sourceFileData) {
            if (sourceFileData instanceof RequestFailed) {
              console.error("Failed to file contents for " + fileName + " , " +
                sourceFileData);
            } else {
              editor._setContentAttr(sourceFileData.fileContent);
              editor.setBugMarkers(that.runId, that.viewedFile);
              editor.setFileName(that.viewedFile.split("/").pop());
              editor.setPath(that.viewedFile);

              var newRange = that.createRangeFromBugPos(item.range);
              that.jumpToRangeAndDrawBubblesLines(editor, newRange, item.reportId);
            }
          });

        } else {
          var newRange = that.createRangeFromBugPos(item.range);
          that.jumpToRangeAndDrawBubblesLines(editor, newRange, item.reportId);
        }

        that.currCheckerId = item.checkerId;
        that.reportId = item.reportId;

        that.set("title", checkedFile.split(/[\/]+/).pop() + " @ Line " + item.range.startLine);

        if (item.suppressed === false && CCV.isSupprFileAvailable) {
          editorHeader.suppressButton.setDisabled(false);
        }

      }
    };


    editorHeader.documentationButton.onClick = function () {
      myOverviewTC.showDocumentation(that.currCheckerId);
    };


    editorHeader.suppressButton.onClick = function () {
      var suppressDialog = new Dialog({
        title : "Comment for the suppress",
        style : "text-align: center;"
      });

      var suppressTextarea = new Textarea({
        maxLength : 1024
      });

      var sendSuppressButton = new Button({
        label   : "Suppress",
        onClick : function () {

          sendSuppressButton.setDisabled(true);

          CC_SERVICE.suppressBug(
            [runId],
            that.reportId,
            suppressTextarea.getValue(),
            function (result) {
              if (result instanceof RequestFailed) {
                console.log("Thrift API call 'suppressBug' failed!");

                var errorDialog = new Dialog({
                  title   : "Error",
                  content : "Failed to suppress bug."
                });

                suppressDialog.hide();

                errorDialog.show();
              } else {
                editorHeader.suppressButton.setDisabled(true);

                CCV.reset();

                myOverviewTC.overviewGrid.refreshGrid();

                that.bugStoreModelTree.bugStore.remove(that.bugStoreModelTree.bugTree.selectedItem.parent);

                that.clearSelectionAndBubblesLines(editor);

                editor.setBugMarkers(that.runId, that.viewedFile);

                suppressDialog.hide();
              }
            }
          );

        }
      });

      suppressDialog.addChild(suppressTextarea);
      suppressDialog.addChild(sendSuppressButton);

      suppressDialog.show();
    };


    if (suppressed === true) {
      editorHeader.suppressButton.setDisabled(true);
    }

    CC_SERVICE.getSourceFileData(that.viewedFileId, true, function (sourceFileData) {
      if (sourceFileData instanceof RequestFailed) {
        console.error("Failed to file contents for " + fileName + " , " +
          sourceFileData);
      } else {
        editor._setContentAttr(sourceFileData.fileContent);
        editor.setFileName(that.viewedFile.split("/").pop());
        editor.setPath(that.viewedFile);
        editor.setBugMarkers(that.runId, that.viewedFile);

        var newRange = that.createRangeFromBugPos(lastBugPosition);
        that.jumpToRangeAndDrawBubblesLines(editor, newRange, reportId);
      }
    });


    treePane.addChild(that.bugStoreModelTree.bugTree);
    editorCP.addChild(editor);
    editorHeaderCP.addChild(editorHeader);

    editorBC.addChild(editorCP);
    editorBC.addChild(editorHeaderCP);

    that.addChild(treePane);
    that.addChild(editorBC);
  },

  /**
   * Scrolls to a given range in the Editor widget and draws bug bubbles and
   * step-lines according to the currently selected bug or bugstep.
   *
   * @param editor The appropriate Editor widget
   * @param range The range we want to scroll to
   * @param reportId The reportId of the selected bug
   */
  jumpToRangeAndDrawBubblesLines : function (editor, range, reportId) {
    var that = this;

    editor.clearBubbles();
    editor.clearLines();

    var filterFunction = function (obj) {
      if (obj.fileId === that.viewedFileId) {
        return true;
      } else {
        return false;
      }
    };

    CC_SERVICE.getReportDetails(reportId, function (reportDetails) {
      if (reportDetails instanceof RequestFailed) {
        console.log("Thrift API call 'getReportDetails' failed!");
      } else {
        var allPoints = reportDetails.executionPath;

        that.createAndAddFileJumpBubbles(allPoints, editor);

        var points  = allPoints.filter(filterFunction);
        var bubbles = reportDetails.pathEvents.filter(filterFunction);

        // This is needed because CodeChecker gives different positions.
        points.forEach(function (point)   { --point.startCol;  });
        bubbles.forEach(function (bubble) { --bubble.startCol; });

        editor.addBubbles(bubbles);
        editor.addLines(points);
      }

      var fln = editor.codeMirror.options.firstLineNumber;

      var newPoint = editor.codeMirror.doc.markText(
        { line : range.from.line - fln, ch : range.from.column - 1 },
        { line : range.to.line   - fln, ch : range.to.column - 1   },
        { className : "codemirrorselection" });
      editor._lineMarks.push(newPoint);

      editor.jumpTo(range.from.line, range.from.column);
    });

  },

  /**
   * Clears the Editor widget of all lines and bubbles.
   *
   * @param editor The appropriate Editor widget
   */

  clearSelectionAndBubblesLines : function (editor) {
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

  /**
   * Creates a range from a bug position
   *
   * @param bugPosition The bug position
   */
  createRangeFromBugPos : function (bugPosition) {
    return {
      from : { line : bugPosition.startLine , column : bugPosition.startCol   },
      to   : { line : bugPosition.endLine   , column : bugPosition.endCol + 1 }
    };

  },

  /**
   * Creates and adds the special jump-to-other-file bubble in an Editor
   *
   * @param points The steps in the executionPath
   * @param editor The appropriate Editor widget
   */
  createAndAddFileJumpBubbles : function (points, editor) {
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
          line       : lastStartLine - 1,
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

    bubbleInfoArray.forEach(function (e, i) {
      editor.addNewOtherFileBubble(
        e.filePath,
        e.fileId,
        e.line,
        e.fileViewBC
      );
    });
  }


});});
