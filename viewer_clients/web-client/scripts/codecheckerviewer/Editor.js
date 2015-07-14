// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  "dojo/_base/declare",
  "dojo/_base/window",
  "dojo/dom-construct",
  "dojo/dom-style",
  "dojo/on",
  "dojo/query",
  "dijit/_WidgetBase"
], function ( declare, window, dom, style, on, query, _WidgetBase ) {


  function refresh(editor) {
    var headerHeight = style.get(editor._domElements.header, "height");
    var newHeight = style.get(editor.editorCP.srcNodeRef, "height") - headerHeight - 7;

    style.set(editor.srcNodeRef, "height", newHeight + "px");

    editor.codeMirror.refresh();
  }


  function resetJsPlumb(editor) {
    if (editor.jsPlumbInstance)
      editor.jsPlumbInstance.reset();

    // The position of thie DOM element is set to relative so jsPlumb lines
    // work properly in the text view.
    var jsPlumbParentElement
      = query('.CodeMirror-lines', editor.codeMirror.getWrapperElement())[0];
    style.set(jsPlumbParentElement, 'position', 'relative');

    editor.jsPlumbInstance = jsPlumb.getInstance({
      Container : jsPlumbParentElement,
      Anchor     : ['Perimeter', { shape : 'Ellipse' }],
      Endpoint   : ['Dot', { radius : 1 }],
      PaintStyle : { strokeStyle : 'blue', lineWidth : 1 },
      ConnectionsDetachable : false,
      ConnectionOverlays    : [['Arrow',
        { location : 1, length : 10, width : 8 }]]
    });
  }


  function lineDrawer(editor, from, to) {

    if (editor._lineMarks.length === 0)
      return;

    /**
     * This function returns the &lt;span&gt; element which belongs to the given
     * textMarker.
     * @param {TextMarker} textMarker CodeMirror object.
     * @return {Object|Null} A DOM object which belongs to the given text marker
     * or null if not found.
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
      '.CodeMirror-code', editor.codeMirror.getWrapperElement())[0].children;
    var spans = {};
    var markers = {};

    editor._lineMarks.forEach(function (textMarker) {
      // If not in viewport
      try {
        var line = textMarker.lines[0].lineNo();
      } catch (ex) {
        return;
      }
      if (line < from || line >= to)
        return;

      spans[line] = query('.checkerstep', cmLines[line - from]);

      if (markers[line])
        markers[line].push(textMarker);
      else
        markers[line] = [textMarker];
    });

    // Sort the markers by the position of their start point in the given line,
    // so that they are placed on the same index as the corresponding <span>
    // element in the array "spans".
    for (var line in markers)
      markers[line].sort(function (left, right) {
        return left.find().from.ch - right.find().from.ch;
      });

    resetJsPlumb(editor);

    var prev;
    editor._lineMarks.forEach(function (textMarker) {
      var current = getSpanToMarker(textMarker);

      if (!current)
        return;

      if (prev)
        editor.jsPlumbInstance.connect({
          source : prev,
          target : current
        });

      prev = current;
    });
  }


  return declare(_WidgetBase, {

    refresh: function () {
      this.codeMirror.refresh();
    },

    addNewOtherFileBubble: function (file, fileId, line, fileViewBC) {
      var that = this;


      var element = dom.create("div", {
        style     : "margin-left: 200px",
        class     : "otherFileMsg",
        innerHTML : "bugpath in:<br>" + file.split("/").pop(),
      });

      element.onclick = function () {
        that._setContentAttr(CC_SERVICE.getSourceFileData(fileId, true).fileContent);
        that.setFileName(file.split("/").pop());
        that.setPath(file);
        fileViewBC.viewedFile = file;
        fileViewBC.viewedFileId = fileId;
      };

      that._lineWidgets.push(that.codeMirror.addLineWidget(line, element));
    },

    constructor : function () {
      var that = this;

      this._lineWidgets = [];
      this._lineMarks = [];

      on(window.global, 'resize', function () { refresh(that); });
    },


    buildRendering : function () {
      var that = this;

      //--- DOM elements ---//

      if (this.srcNodeRef) {
        require(['dojo/dom-class'], function (domClass) {
          if (!domClass.contains(that.srcNodeRef, 'editor'))
            domClass.add(that.srcNodeRef, 'editor');
        });
      }

      this._domElements = {
        editor  : this.srcNodeRef || dom.create('div', { class : 'editor' }),
        header  : dom.create('div', { class : 'header' }),
        filename: dom.create('span', { class : 'filename' }),
        path    : dom.create('span', { class : 'path' }),
        colons  : dom.toDom('<span class="colons"> : </span>')
      };

      //dom.place(this._domElements.filename, this._domElements.header);

      this.domNode = this._domElements.editor;

      //--- Add header ---//

      dom.place(this._domElements.header, this._domElements.editor);
      dom.place(this._domElements.filename, this._domElements.header);
      dom.place(this._domElements.colons, this._domElements.header);
      dom.place(this._domElements.path, this._domElements.header);

      //--- Create CodeMirror ---//

      this.codeMirror = new CodeMirror(this._domElements.editor, {
        matchBrackets   : this.matchBrackets,
        firstLineNumber : this.firstLineNumber,
        lineNumbers     : this.lineNumbers,
        readOnly        : this.readOnly,
        mode            : this.mode,
        foldGutter      : true,
        gutters         : ["CodeMirror-linenumbers", "CodeMirror-foldgutter"]
      });

      this.codeMirror.setSize("100%", "100%");

      this.codeMirror.on('viewportChange', function (cm, from, to) {
        lineDrawer(that, from, to);
      });

      // Save default line number formatter so we can reset
      this._cmDefaultLineNumberFormatter
        = this.codeMirror.getOption("lineNumberFormatter");

      refresh(this);

    },


    setFileName : function (fileName) {
      dom.place(dom.toDom(fileName), this._domElements.filename, 'only');
    },


    setPath : function (path) {
      dom.place(dom.toDom(path), this._domElements.path, 'only');
    },


    addBubbles : function (bubbles) {
      var that = this;

      var fln = this.codeMirror.options.firstLineNumber;

      bubbles.forEach(function (bubble) {
        var left = that.codeMirror.defaultCharWidth() * bubble.startCol + 'px';

        var element = dom.create('div', {
          style     : 'margin-left: ' + left,
          class     : 'checkMsg',
          innerHTML : bubble.msg
        });

        that._lineWidgets.push(that.codeMirror.addLineWidget(
          bubble.startLine - fln, element));
      });

      //that.createNewDummyBubble("valami1/valam2/valami3.c");
    },


    clearBubbles : function () {
      this._lineWidgets.forEach(function (widget) { widget.clear(); });
      this._lineWidgets = [];
    },


    addLines : function (points) {
      var fln = this.codeMirror.options.firstLineNumber;

      for (var i = 0; i < points.length; ++i) {
        var point = this.codeMirror.doc.markText(
          { line : points[i].startLine - fln, ch : points[i].startCol },
          { line : points[i].endLine   - fln, ch : points[i].endCol   },
          { className : 'checkerstep' });
        this._lineMarks.push(point);
      }

      var range = this.codeMirror.getViewport();
      lineDrawer(this, range.from, range.to);
    },


    clearLines : function () {
      resetJsPlumb(this);
      this._lineMarks.forEach(function (mark) { mark.clear(); });
      this._lineMarks = [];
    },


    /**
     * This function sets the text of the CodeMirror window.
     * @param {String} content Content of the CodeMirror window.
     * TODO: This function should also set the 'mode' attribute for syntax
     * highlight in CodeMirror.
     */
    _setContentAttr : function (content) {
      this.codeMirror.doc.setValue(content);

      refresh(this);
    },

    /**
     * This function returns the text of the CodeMirror window.
     */
    _getContentAttr : function () {
      return this.codeMirror.doc.getValue();
    },

    /**
     * This function returns the given line as a string.
     * @param {Number} line Line number
     */
    getLine : function (line) {
      return this.codeMirror.doc.getLine(line - 1);
    },


    /**
     * This function jumps to the given position.
     * @param {Number} line Line number.
     * @param {Number} column Column number.
     */
    jumpTo : function (line, column) {
      var that = this;
      setTimeout(function () {
        var selPosPixel
          = that.codeMirror.charCoords({ line : line, ch : column }, 'local');
        var editorSize = {
          width  : style.get(that._domElements.editor, 'width'),
          height : style.get(that._domElements.editor, 'height')
        };

        that.codeMirror.scrollIntoView({
          top    : selPosPixel.top - 100,
          bottom : selPosPixel.top + editorSize.height - 150,
          left   : selPosPixel.left < editorSize.width - 100
                 ? 0
                 : selPosPixel . left - 50,
          right  : selPosPixel.left < editorSize.width - 100
                 ? 10
                 : selPosPixel.left + editorSize.width - 100
        });
      }, 0);
    },

    /**
     * This function selects the given range.
     * @param {Object} range Range of the selection which contains a 'from' and
     * 'to' attribute. These attributes are also ojects with 'line' and 'column'
     * attributes.
     */
    _setSelectionAttr : function (range) {
      var that = this;
      setTimeout(function () {
        that.codeMirror.doc.setSelection(
          { line : range.from.line - 1, ch : range.from.column - 1 },
          { line : range.to.line   - 1, ch : range.to.column   - 1 },
          { scroll: true } );
      }, 0);
    },

    /**
     * This function returns the selected range if any. If there is no selected
     * range then it returns the cursor position.
     */
    _getSelectionAttr : function () {
      var from = this.codeMirror.doc.getCursor('start');
      var to   = this.codeMirror.doc.getCursor('end');

      return {
        from : { line : from.line + 1, column : from.ch + 1 },
        to   : { line : to.line   + 1, column : to.ch   + 1 }
      };
    },

    /**
     * This function returns a token info at the given position. In the
     * returning object there are properties like 'start' and 'end' which
     * determine the border positions of the token, 'string' which is the
     * token's text, 'type' like keyword, comment, etc. and 'state'.
     * @param {Object} pos This is a coordinate object which has to have 'line'
     * and 'column' properties.
     */
    getTokenAt : function (pos) {
      var token = this.codeMirror.getTokenAt({
        line : pos.line - this.codeMirror.options.firstLineNumber,
        ch   : pos.column
      });

      ++token.start;
      ++token.end;

      return token;
    },

    /**
     * This function returns the word under the clicked position. A string is
     * considered to be a word if its characters match the /[a-z0-9_]/i pattern.
     * @param {Object} pos This is a coordinate object which has to have 'line'
     * and 'column' properties.
     */
    getWordAt : function (pos) {
      var pattern = /[a-z0-9_]/i;

      var line = this.codeMirror.getLine(
        pos.line - this.codeMirror.options.firstLineNumber);

      var start = pos.column - 1;
      while (start > -1 && line[start].match(pattern))
        --start;
      var end = pos.column - 1;
      while (end < line.length && line[end].match(pattern))
        ++end;

      return {
        string : line.substring(start + 1, end),
        start  : start + 2,
        end    : end + 1
      };
    },

    /**
     * This function returns the selected text.
     */
    getSelectedText : function () {
      return this.codeMirror.getRange(
        this.codeMirror.doc.getCursor('start'),
        this.codeMirror.doc.getCursor('end'));
    },

    /**
     * This function returns the search input field's DOM node if any.
     */
    getSearchInput : function () {
      var searchInput = null;
      require(['dojo/dom'], function (dom) {
        searchInput = dom.byId('searchinput');
      });
      return searchInput;
    },

    /**
     * This function calls the markText() function of CodeMirror, thus its
     * options are the same except that 'from' and 'to' objects has to have
     * 'line' and 'column' attributes.
     * @param {Object} from Mark text from this position.
     * @param {Object} to Mark text till this position.
     * @param {Object} options Pass these options to CodeMirror's markText
     * function.
     * @return {Number} This function returns an id which can be passed to
     * clearMark() function to remove this selection.
     */
    markText : function (from, to, options) {
      var fln = this.codeMirror.options.firstLineNumber;

      this._marks[this._markIdCounter] = this.codeMirror.markText(
        { line : from.line - fln, ch : from.column - 1 },
        { line : to.line   - fln, ch : to.column   - 1 },
        options);

      return this._markIdCounter++;
    },

    /**
     * This function clears a text mark.
     * @param {Number} markId Id of the selection to remove.
     */
    clearMark : function (markId) {
      this._marks[markId].clear();
      delete this._marks[markId];
    },

    clearAllMarks : function () {
      for (var markId in this._marks)
        this.clearMark(markId);
    },

    /**
     * This function is the same as CodeMirror's getScrollInfo() function. The
     * returning object has the following properties: left, top, width, height,
     * clientWidth, clientHeight
     */
    getScrollInfo : function () {
      return this.codeMirror.getScrollInfo();
    },

    /**
     * This function resizes the editor element. It's recommended to use this
     * function for resizing instead of resizing the domNode directly, because
     * this way the editor's content is also refreshed.
     * @param {Object} size New size of the editor. This object can have a
     * 'width' and 'height' property.
     */
    _setSizeAttr : function (size) {
      if (size.width)
        style.set(this._domElements.editor, 'width',  size.width);
      if (size.height)
        style.set(this._domElements.editor, 'height', size.height);

      refresh(this);
    },

    /**
     * This function returns the size of the editor. The returning object has a
     * 'width' and 'height' attribute.
     */
    _getSizeAttr : function () {
      return {
        width  : this._domElements.editor.style.width,
        height : this._domElements.editor.style.height
      };
    },

    /**
     * This function sets the position of the editor.
     * @param {Object} position Position object which has a 'top' and 'left'
     * attribute.
     */
    _setPositionAttr : function (position) {
      if (position.top)
        style.set(this._domElements.editor, 'top',  position.top);
      if (position.left)
        style.set(this._domElements.editor, 'left', position.left);
    },

    /**
     * This function returns the position of the editor. The returning object
     * has a 'top' and a 'left' attribute.
     */
    _getPositionAttr : function () {
      return {
        top  : this._domElements.editor.style.top,
        left : this._domElements.editor.style.left
      };
    },

    /**
     * By this function one can set the highlighting mode of the editor.
     * @param {String} mode Source code highlighting mode. See possible values
     * here: http://codemirror.net/mode/
     */
    _setModeAttr : function (mode) {
      this.codeMirror.setOption('mode', mode);
      this.mode = mode;
    },

    /**
     * This function sets whether the search bar should be displayed or not.
     * @param {Boolean} display True if display should always be seen.
     */
    _setDisplaySearchAttr : function (display) {
      this.displaySearch = display;
      this.codeMirror.execCommand("find");
      refresh(this);
    },

    /**
     * This function can be used to refresh the editor.
     */
    resize : function () { refresh(this); },

    /**
     * By this function one can format the line numbers.
     * @param {Function} formatter This is a callback function which gets a
     * line number as parameter and has to return the text of a decorated
     * line number as String or as a DOM node. If the parameter is not set
     * then simple line numbers will be used.
     * TODO: actually a one element array which contains a DOM node.
     */
    setLineNumberFormatter : function (formatter) {
      this.codeMirror.setOption(
        "lineNumberFormatter",
        formatter || this._cmDefaultLineNumberFormatter);
    },

    /**
     * This function returns the line and column based on a given position in
     * pixels. The returning object has 'line' and 'column' properties.
     * @param {Object} pos The position object has to have an 'x' and 'y'
     * property.
     */
    lineColByPosition : function (pos) {
      var pos = this.codeMirror.coordsChar({
        left : pos.x,
        top  : pos.y
      });

      return {
        line   : pos.line + this.codeMirror.options.firstLineNumber,
        column : pos.ch + 1
      };
    },


    firstLineNumber : 1,
    lineNumbers     : true,
    readOnly        : true,
    matchBrackets   : true,
    mode            : 'text/x-c++src',
    resizable       : false,
    draggable       : false,
    closable        : false,
    displaySearch   : false,

    onClose           : function () {},
    onClick           : function () {},
    onCtrlClick       : function () {},
    onRightClick      : function () {},
    onCtrlRightClick  : function () {},
    onMiddleClick     : function () {},
    onCtrlMiddleClick : function () {},
    onResize          : function () {},
    onSelectionChange : function () {}



  });
});
