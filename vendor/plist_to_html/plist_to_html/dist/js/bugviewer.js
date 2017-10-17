var BugViewer = {
  _files : [],
  _reports : [],
  _lineWidgets : [],
  _sourceFileData : null,
  _currentReport : null,
  _lastBugEvent  : null,

  init : function (files, reports) {
    this._files = files;
    this._reports = reports;
  },

  create : function () {
    this._content = document.getElementById('editor-wrapper');
    this._filepath = document.getElementById('file-path');
    this._editor = document.getElementById('editor');

    this._codeMirror = CodeMirror(this._editor, {
      mode: 'text/x-c++src',
      matchBrackets : true,
      lineNumbers : true,
      readOnly : true,
      foldGutter : true,
      extraKeys : {},
      viewportMargin : 100
    });

    this._createNavigationMenu();
  },

  _createNavigationMenu : function () {
    var that = this;

    var nav = document.getElementById('report-nav');
    var list = document.createElement('ul');
    this._reports.forEach(function (report) {
      var lastBugEvent = report[report.length - 1];
      var item = document.createElement('li');
      item.innerHTML = lastBugEvent.msg;
      item.addEventListener('click', function () {
        that._selectedReport.classList.remove('active');
        that._selectedReport = this;
        that._selectedReport.classList.add('active');
        that.setReport(report);
      })
      list.appendChild(item);
    });

    if (!this._selectedReport && list.childNodes.length) {
      this._selectedReport = list.childNodes[0];
      this._selectedReport.classList.add('active');
    }

    nav.appendChild(list);
  },

  setReport : function (report) {
    this._currentReport = report;
    var lastBugEvent = report[report.length - 1];
    this.setCurrentBugEvent(lastBugEvent);
  },

  setCurrentBugEvent : function (event) {
    this._currentBugEvent = event;
    this.setSourceFileData(this._files[event.file]);

    this.jumpTo(event.line, 0)
  },

  setSourceFileData : function (file) {
    this._sourceFileData = file;
    this._filepath.innerHTML = file.path;
    this._codeMirror.doc.setValue(file.content);
    this._refresh();

    this.drawBugPath();
  },

  _refresh : function () {
    var that = this;
    setTimeout(function () {
      var fullHeight = parseInt(that._content.clientHeight);
      var headerHeight = that._filepath.clientHeight;

      that._codeMirror.setSize('auto', fullHeight - headerHeight);
      that._codeMirror.refresh();
    }, 200);
  },

  clearBubbles : function () {
    this._lineWidgets.forEach(function (widget) { widget.clear(); });
    this._lineWidgets = [];
  },

  drawBugPath : function () {
    var that = this;

    this.clearBubbles();

    this._currentReport.forEach(function (bugEvent, i) {
      if (bugEvent.file !== that._currentBugEvent.file)
        return;

      var left = that._codeMirror.defaultCharWidth() * bugEvent.col + 'px';
      var type = i == that._currentReport.length - 1 ? 'error' : 'info';

      var element = document.createElement('div');
      element.setAttribute('style', 'margin-left: ' + left);
      element.setAttribute('class', 'check-msg ' + type);

      var enumeration = document.createElement('span');
      enumeration.setAttribute('class', 'checker-enum ' + type);
      enumeration.innerHTML = bugEvent.step;

      if (that._currentReport.length > 1)
        element.appendChild(enumeration);

      var prevBugEvent = bugEvent.step - 1;
      if (prevBugEvent > 0) {
        var prevBug = document.createElement('span');
        prevBug.setAttribute('class', 'arrow left-arrow');
        prevBug.addEventListener('click', function () {
          var event = that._currentReport[prevBugEvent - 1];
          that.setCurrentBugEvent(event);
        });
        element.appendChild(prevBug);
      }

      var msg = document.createElement('span');
      msg.innerHTML = bugEvent.msg;
      element.appendChild(msg);

      var nextBugEvent = bugEvent.step;
      if (nextBugEvent < that._currentReport.length) {
        var nextBug = document.createElement('span');
        nextBug.setAttribute('class', 'arrow right-arrow');
        nextBug.addEventListener('click', function () {
          var event = that._currentReport[nextBugEvent];
          that.setCurrentBugEvent(event);
        });
        element.appendChild(nextBug);
      }


      that._lineWidgets.push(that._codeMirror.addLineWidget(
        bugEvent.line - 1, element));
    });
  },

  jumpTo : function (line, column) {
    var that = this;

    setTimeout(function () {
      var selPosPixel
        = that._codeMirror.charCoords({ line : line, ch : column }, 'local');
      var editorSize = {
        width  : that._editor.clientWidth,
        height : that._editor.clientHeight
      };

      that._codeMirror.scrollIntoView({
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
  }
}
