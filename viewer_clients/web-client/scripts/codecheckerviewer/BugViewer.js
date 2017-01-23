define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/dom-style',
  'dojo/on',
  'dojo/query',
  'dojo/store/Memory',
  'dojo/store/Observable',
  'dojo/topic',
  'dijit/Dialog',
  'dijit/tree/ObjectStoreModel',
  'dijit/layout/ContentPane',
  'dijit/layout/BorderContainer',
  'dijit/form/Button',
  'dijit/form/CheckBox',
  'dijit/form/Textarea',
  'dijit/Tooltip',
  'codechecker/HtmlTree',
  'codechecker/util',
  'codechecker/hashHelper'],
function (declare, dom, style, on, query, Memory, Observable, topic,
  Dialog, ObjectStoreModel, ContentPane, BorderContainer, Button, CheckBox,
  Textarea, Tooltip, HtmlTree, util, hashHelper) {

  function resetJsPlumb(editor) {
    if (editor.jsPlumbInstance)
      editor.jsPlumbInstance.reset();

    // The position of this DOM element is set to relative so jsPlumb lines work
    // properly in the text view.
    var jsPlumbParentElement
      = query('.CodeMirror-lines', editor.codeMirror.getWrapperElement())[0];
    style.set(jsPlumbParentElement, 'position', 'relative');

    editor.jsPlumbInstance = jsPlumb.getInstance({
      Container : jsPlumbParentElement,
      Anchor : ['Perimeter', { shape : 'Ellipse' }],
      Endpoint : ['Dot', { radius : 1 }],
      PaintStyle : { strokeStyle : 'blue', lineWidth : 1 },
      ConnectionsDetachable : false,
      ConnectionOverlays : [['Arrow',
        { location : 1, length : 10, width : 8 }]]
    });
  }

  function getFullHeight(element) {
    var computedStyle = style.getComputedStyle(element);

    var height = parseInt(computedStyle.height);
    var paddingTop = parseInt(computedStyle.paddingTop);
    var paddingBottom = parseInt(computedStyle.paddingBottom);
    var borderTop = parseInt(computedStyle.borderTopWidth);
    var borderBottom = parseInt(computedStyle.borderBottomWidth);
    var marginTop = parseInt(computedStyle.marginTop);
    var marginBottom = parseInt(computedStyle.marginBottom);

    return height + paddingTop + paddingBottom + borderTop + borderBottom +
      marginTop + marginBottom;
  }

  var Editor = declare(ContentPane, {
    constructor : function () {
      this._lineWidgets = [];
      this._lineMarks = [];

      this.style = 'padding: 0;';
    },

    postCreate : function () {
      var that = this;

      this.filepath = dom.create('div', { class : 'editorHeader' });
      dom.place(this.filepath, this.domNode);

      this.codeMirror = new CodeMirror(this.domNode, {
        matchBrackets : true,
        lineNumbers : true,
        readOnly : true,
        mode : 'text/x-c++src',
        foldGutter : true,
        gutters : ['CodeMirror-linenumbers', 'bugInfo'],
        extraKeys : {},
        viewportMargin : 500
      });

      this.codeMirror.on('viewportChange', function (cm, from, to) {
        that._lineDrawer(from, to);
      });

      on(document, 'keydown', function (event) {
        if (event.keyCode === 13) // Enter
          that.codeMirror.execCommand('findPersistentNext');

        if (event.ctrlKey && event.keyCode === 70) { // Ctrl-f
          event.preventDefault();
          that.codeMirror.execCommand('findPersistent');
        }
      });
    },

    resize : function () {
      this.inherited(arguments);
      this._refresh();
    },

    drawBugPath : function () {
      var that = this;

      this.clearBubbles();
      this.clearLines();

      function filterFunction(obj) {
        return obj.fileId === that.sourceFileData.fileId;
      }

      var reportDetails = CC_SERVICE.getReportDetails(this.reportData.reportId);

      var points = reportDetails.executionPath.filter(filterFunction);
      var bubbles = reportDetails.pathEvents.filter(filterFunction);

      // This is needed because CodeChecker gives different positions.
      points.forEach(function (point) { --point.startCol; });
      points.forEach(function (bubble) { --bubble.startCol; });

      that.addBubbles(bubbles);
      that.addLines(points);
      that.addOtherFileBubbles(reportDetails.executionPath);
    },

    addBubbles : function (bubbles) {
      var that = this;

      bubbles.forEach(function (bubble) {
        var left = that.codeMirror.defaultCharWidth() * bubble.startCol + 'px';

        var element = dom.create('div', {
          style : 'margin-left: ' + left,
          class : 'checkMsg',
          innerHTML : bubble.msg
        });

        that._lineWidgets.push(that.codeMirror.addLineWidget(
          bubble.startLine - 1, element));
      });
    },

    addOtherFileBubbles : function (path) {
      var that = this;

      for (var i = 1; i < path.length; ++i) {
        if (path[i].fileId !== this.sourceFileData.fileId &&
            path[i].fileId !== path[i - 1].fileId) {
          var element = dom.create('div', {
            class : 'otherFileMsg',
            innerHTML : 'bugpath in:<br>' + path[i].filePath.split('/').pop(),
            onclick : (function (i) {
              return function () {
                that.set(
                  'sourceFileData',
                  CC_SERVICE.getSourceFileData(path[i].fileId, true));
                that.drawBugPath();
                that.jumpTo(path[i].startLine, path[i].startCol);
              };
            })(i)
          });

          this._lineWidgets.push(this.codeMirror.addLineWidget(
            path[i - 1].startLine - 1, element));
        }
      }
    },

    clearBubbles : function () {
      this._lineWidgets.forEach(function (widget) { widget.clear(); });
      this._lineWidgets = [];
    },

    addLines : function (points) {
      var that = this;

      points.forEach(function (p, i) {
        that._lineMarks.push(that.codeMirror.doc.markText(
          { line : p.startLine - 1, ch : p.startCol + 1 },
          { line : p.endLine - 1,   ch : p.endCol       },
          { className : 'checkerstep' }));
      });

      var range = this.codeMirror.getViewport();
      this._lineDrawer(range.from, range.to);
    },

    clearLines : function () {
      this._lineMarks.forEach(function (mark) { mark.clear(); });
      this._lineMarks = [];
      resetJsPlumb(this);
    },

    jumpTo : function (line, column) {
      var that = this;

      setTimeout(function () {
        var selPosPixel
          = that.codeMirror.charCoords({ line : line, ch : column }, 'local');
        var editorSize = {
          width : style.get(that.domNode, 'width'),
          height : style.get(that.domNode, 'height')
        };

        that.codeMirror.scrollIntoView({
          top    : selPosPixel.top - 100,
          bottom : selPosPixel.top + editorSize.height - 150,
          left   : selPosPixel.left < editorSize.width - 100
                 ? 0
                 : selPosPixel.left - 50,
          right  : selPosPixel.left < editorSize.width - 100
                 ? 10
                 : selPosPixel.left + editorSize.width - 100
        });
      }, 0);
    },

    highlightBugPathEvent : function (bugPathEvent) {
      if (this._currentLineMark)
        this._currentLineMark.clear();

      this._currentLineMark = this.codeMirror.doc.markText(
        { line : bugPathEvent.startLine - 1, ch : bugPathEvent.startCol - 1 },
        { line : bugPathEvent.endLine - 1,   ch : bugPathEvent.endCol       },
        { className : 'currentMark' });
    },

    _setContentAttr : function (content) {
      this.codeMirror.doc.setValue(content);
      this._refresh();
    },

    _setFilepathAttr : function (filepath) {
      this.filepath.innerHTML = filepath;
    },

    _setSourceFileDataAttr : function (sourceFileData) {
      this.sourceFileData = sourceFileData;
      this.set('content', sourceFileData.fileContent);
      this.set('filepath', sourceFileData.filePath);
      this.jumpTo(this.reportData.lastBugPosition.startLine, 0);
    },

    _refresh : function () {
      var that = this;
      setTimeout(function () {
        var fullHeight = parseInt(style.getComputedStyle(that.domNode).height);
        var headerHeight = getFullHeight(that.filepath);

        that.codeMirror.setSize('100%', (fullHeight - headerHeight) + 'px');
        that.codeMirror.refresh();
      }, 0);
    },

    _lineDrawer : function (from, to) {
      if (this._lineMarks.length === 0)
        return;

      var that = this;

      /**
       * This function returns the <span> element which belongs to the given
       * textmarker.
       * @param {TextMarker} textMarker CodeMirror object.
       * @return {Object|Null} A DOM object which belongs to the given text
       * marker or null if not found.
       * @pre This function assumes that the "spans" and "markers" variables
       * contain the corresponding DOM elements and markers at the same
       * position.
       */
      function getSpanToMarker(textMarker) {
        for (var line in markers) {
          var idx = markers[line].indexOf(textMarker);
          if (idx !== -1)
            return spans[line][idx];
        }
        return null;
      }

      var cmLines = query(
        '.CodeMirror-code', this.codeMirror.getWrapperElement())[0].children;
      var spans = {};
      var markers = {};

      this._lineMarks.forEach(function (textMarker) {
        // If not in viewport
        try {
          var line = textMarker.lines[0].lineNo();
        } catch (ex) {
          return;
        }

        if (line < from || line >= to)
          return;

        spans[line] = [];
        query('.checkerstep', cmLines[line - from]).forEach(function (step) {
          var count
            = (step.getAttribute('class').match(/checkerstep/g) || []).length;
          for (var i = 0; i < count; ++i)
            spans[line].push(step);
        });

        if (markers[line])
          markers[line].push(textMarker);
        else
          markers[line] = [textMarker];
      });

      // Sort the markers by the position of their start point in the given
      // line, so that they are placed on the same index as the corresponding
      // <span> element in the array "spans".
      for (var line in markers)
        markers[line].sort(function (left, right) {
          return left.find().from.ch - right.find().from.ch;
        });

      resetJsPlumb(this);

      var prev;
      this._lineMarks.forEach(function (textMarker) {
        var current = getSpanToMarker(textMarker);

        if (!current)
          return;

        if (prev)
          that.jsPlumbInstance.connect({
            source : prev,
            target : current
          });

        prev = current;
      });
    }
  });

  var BugStoreModelTree = declare(HtmlTree, {
    constructor : function () {
      var that = this;

      this.bugStore = new Observable(new Memory({
        data : [{ id : 'root' }],
        getChildren : function (node) {
          return this.query({ parent : node.id });
        }
      }));

      this.model = new ObjectStoreModel({
        store : that.bugStore,
        query : { id : 'root' },
        mayHaveChildren : function (item) {
          return !item.isLeaf;
        }
      });
    },

    postCreate : function () {
      this.inherited(arguments);
      this.loadBugStoreData();

      // When loaded from URL then report data is originally a number.
      // When loaded by clicking on a table row, then severity is already
      // changed to its string representation.
      if (typeof this.reportData.severity === 'number')
        this.reportData.severity
          = util.severityFromCodeToString(this.reportData.severity);

      this.set('path', [
        'root',
        this.reportData.severity,
        this.reportData.reportId + '',
        this.reportData.reportId + '_0'
      ]);
    },

    loadBugStoreData : function () {
      var that = this;

      [
        { id : 'root',        name : 'Bugs by priority' },
        { id : 'critical',    name : 'Critical',    parent : 'root', isLeaf : false },
        { id : 'high',        name : 'High',        parent : 'root', isLeaf : false },
        { id : 'medium',      name : 'Medium',      parent : 'root', isLeaf : false },
        { id : 'low',         name : 'Low',         parent : 'root', isLeaf : false },
        { id : 'style',       name : 'Style',       parent : 'root', isLeaf : false },
        { id : 'unspecified', name : 'Unspecified', parent : 'root', isLeaf : false }
      ].forEach(function (item) {
        that.bugStore.put(item);
      });

      var endPos = this.reportData.checkedFile.indexOf(' ');
      if (endPos === -1)
        endPos = this.reportData.checkedFile.length;

      var filepath = this.reportData.checkedFile.substr(0, endPos);

      var filter_sup = new CC_OBJECTS.ReportFilter();
      filter_sup.filepath = filepath;
      filter_sup.suppressed = true;

      var filter_unsup = new CC_OBJECTS.ReportFilter();
      filter_unsup.filepath = filepath;
      filter_unsup.suppressed = false;

      CC_SERVICE.getRunResults(
        this.runData.runId,
        CC_OBJECTS.MAX_QUERY_SIZE,
        0,
        [],
        [filter_sup, filter_unsup],
        function (result) {
          result.forEach(function (report) { that._addReport(report); });

          that.bugStore.query({ parent : 'root' }).forEach(function (severity) {
            if (that.bugStore.query({ parent : severity.id }).length === 0)
              that.bugStore.remove(severity.id);
          });
        });
    },

    onClick : function (item) {
      if (!item.isLeaf)
        return;

      var that = this;

      if (item.bugPathEvent) {
        var fileId = item.bugPathEvent.fileId;
        var line = item.bugPathEvent.startLine;
        var column = item.bugPathEvent.startCol;
      } else {
        var fileId = item.report.fileId;
        var line = item.report.lastBugPosition.startLine;
        var column = item.report.lastBugPosition.startCol;
      }

      if (fileId !== this.editor.get('sourceFileData').fileId)
        this.editor.set(
          'sourceFileData',
          CC_SERVICE.getSourceFileData(fileId, true));

      if (this.editor.reportData.reportId != item.parent) {
        this.editor.set('reportData', item.report);
        hashHelper.setReport(item.report.reportId);
      }

      if (this.buttonPane.showArrowCheckbox.get('checked'))
        this.editor.drawBugPath();

      this.editor.jumpTo(line, column);

      if (item.bugPathEvent)
        this.editor.highlightBugPathEvent(item.bugPathEvent);
    },

    _onNodeMouseEnter : function (node) {
      if (node.item.isLeaf)
        Tooltip.show(node.item.name, node.domNode, ['above']);
    },

    _onNodeMouseLeave : function (node) {
      if (node.item.isLeaf)
        Tooltip.hide(node.domNode);
    },

    _addReport : function (report) {
      var that = this;

      this.bugStore.put({
        id : report.reportId + '',
        name : 'Line ' + report.lastBugPosition.startLine + ': ' + report.checkerId,
        parent : util.severityFromCodeToString(report.severity),
        report : report,
        isLeaf : false
      });

      this.bugStore.put({
        id : report.reportId + '_0',
        name : '<b><u>Result</u>: ' + report.checkerMsg + '</b>',
        parent : report.reportId + '',
        report : report,
        isLeaf : true
      });

      CC_SERVICE.getReportDetails(report.reportId, function (reportDetails) {
        reportDetails.pathEvents.forEach(function (step, index) {
          that.bugStore.put({
            id : report.reportId + '_' + (index + 1),
            name : 'Line ' + step.startLine + ': ' + step.msg,
            parent : report.reportId,
            bugPathEvent : step,
            isLeaf : true,
            report : report
          });
        });
      });
    },

    openOnClick : true,
    showRoot : false
  });

  var ButtonPane = declare(ContentPane, {
    style : 'padding: 2px',

    postCreate : function () {
      var that = this;

      function setUnsuppressDialogContent() {
        unsuppressDialog.getChildren().forEach(function (child) {
          unsuppressDialog.removeChild(child);
        });

        unsuppressDialog.set('content', dom.create('div', {
          innerHTML : '<b>Are you sure to unsuppress this bug?</b><br>' +
            that.reportData.suppressComment
        }));

        unsuppressDialog.addChild(sendUnsuppressButton);
      }

      //--- Bug suppression ---//

      var suppressTextarea = new Textarea();
      
      var sendSuppressButton = new Button({
        label : 'Suppress',
        onClick : function () {
          CC_SERVICE.suppressBug(
            [that.runData.runId],
            that.reportData.reportId,
            suppressTextarea.get('value'),
            function (success) {
              if (success) {
                that.reportData.suppressed = true;
                that.reportData.suppressComment = suppressTextarea.get('value');
                setUnsuppressDialogContent();
                that.removeChild(suppressButton);
                that.addChild(unsuppressButton, 0);
                suppressDialog.hide();
              }
            });
        }
      });

      var sendUnsuppressButton = new Button({
        label : 'Unsuppress',
        onClick : function () {
          CC_SERVICE.unSuppressBug(
            [that.runData.runId],
            that.reportData.reportId,
            function (success) {
              that.reportData.suppressed = false;
              that.reportData.suppressComment = null;
              that.removeChild(unsuppressButton);
              that.addChild(suppressButton, 0);
              unsuppressDialog.hide();
            });
        }
      });

      var detailsDialog = new Dialog({ title : 'Report details' });
      var suppressDialog = new Dialog({ title : 'Suppress bug' });
      var unsuppressDialog = new Dialog({ title : 'Unsuppress bug' });

      suppressDialog.addChild(suppressTextarea);
      suppressDialog.addChild(sendSuppressButton);

      setUnsuppressDialogContent();

      var suppressButton = new Button({
        label : 'Suppress bug',
        disabled : !CC_SUPPRESS_FILE_EXISTS,
        onClick : function () { suppressDialog.show(); }
      });

      var unsuppressButton = new Button({
        label : 'Unsuppress bug',
        disabled : !CC_SUPPRESS_FILE_EXISTS,
        onClick : function () { unsuppressDialog.show(); }
      });

      this.addChild(
        this.reportData.suppressed ? unsuppressButton : suppressButton);
      
      //--- Documentation ---//

      this.addChild(new Button({
        label : 'Show documentation',
        onClick : function () {
          topic.publish('showDocumentation', that.reportData.checkerId);
        }
      }));

      //--- Details ---//

      this.addChild(new Button({
        label : 'Details',
        onClick : function () {
          var content = dom.create('div', { class : 'buildActionInfo' });

          CC_SERVICE.getBuildActions(that.reportData.reportId).forEach(
          function (buildAction) {
            var details = dom.create('dl');

            dom.place(
              dom.create('dt', { innerHTML : 'Check command' }), details);
            dom.place(
              dom.create('dd', {
                innerHTML : buildAction.checkCmd || 'Only in debug mode parsing'
              }), details);
            dom.place(
              dom.create('dt', { innerHTML : 'Failure' }), details);
            dom.place(
              dom.create('dd', { innerHTML : buildAction.failure }), details);
            dom.place(
              dom.create('dt', { innerHTML : 'Checked file' }), details);
            dom.place(
              dom.create('dd', { innerHTML : buildAction.file }), details);

            dom.place(details, content);
            dom.place(dom.create('hr'), content);
          });

          detailsDialog.set('content', content);
          detailsDialog.show();
        }
      }));

      //--- Show arrows ---//

      this.showArrowCheckbox = new CheckBox({
        checked : true,
        style : 'margin: 5px;',
        onChange : function (checked) {
          if (checked)
            that.editor.drawBugPath();
          else {
            that.editor.clearLines();
          }
        }
      });

      this.addChild(this.showArrowCheckbox);

      var label = dom.create('label', {
        for : this.showArrowCheckbox.get('id'),
        innerHTML : 'Show arrows'
      });

      dom.place(label, this.showArrowCheckbox.domNode, 'after');
    }
  });

  return declare(BorderContainer, {
    design : 'sidebar',

    postCreate : function () {
      var that = this;

      //--- Editor ---//

      this._editor = new Editor({
        region : 'center',
        reportData : this.reportData,
        runData : this.runData
      });

      CC_SERVICE.getSourceFileData(this.reportData.fileId, true,
      function (sourceFileData) {
        that._editor.set('sourceFileData', sourceFileData);
        that._editor.drawBugPath();
      });

      this.addChild(this._editor);

      //--- Buttons ---//

      var buttonPane = new ButtonPane({
        region : 'top',
        reportData : this.reportData,
        runData : this.runData,
        editor : this._editor
      });

      this.addChild(buttonPane);

      //--- Tree ---//

      var bugStoreModelTree = new BugStoreModelTree({
        region : 'left',
        splitter : true,
        reportData : this.reportData,
        runData : this.runData,
        style : 'width: 300px;',
        editor : this._editor,
        buttonPane : buttonPane
      });

      this.addChild(bugStoreModelTree);
    }
  });
});
