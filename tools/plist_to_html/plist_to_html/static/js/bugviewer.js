// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

var BugViewer = {
  _files : [],
  _reports : [],
  _lineWidgets : [],
  _navigationMenuItems : [],
  _sourceFileData : null,
  _currentReport : null,
  _lastBugEvent  : null,

  init : function (files, reports) {
    this._files = files;
    this._reports = reports;

    this.initEscapeChars();
  },

  initEscapeChars : function () {
    this.escapeChars = {
      ' ' : 'nbsp',
      '<' : 'lt',
      '>' : 'gt',
      '"' : 'quot',
      '&' : 'amp'
    };

    var regexString = '[';
    for (var key in this.escapeChars) {
      regexString += key;
    }
    regexString += ']';

    this.escapeRegExp = new RegExp( regexString, 'g');
  },

  escapeHTML : function (str) {
    var that = this;

    return str.replace(this.escapeRegExp, function (m) {
      return '&' + that.escapeChars[m] + ';';
    });
  },

  initByUrl : function () {
    if (!this._reports) return;

    var state = {};
    window.location.hash.substr(1).split('&').forEach(function (s) {
      var parts = s.split('=');
      state[parts[0]] = parts[1];
    });

    for (var key in this._reports) {
      var report = this._reports[key];
      if (report.reportHash === state['reportHash']) {
        this.navigate(report);
        return;
      }
    }

    this.navigate(this._reports[0]);
  },

  create : function () {
    this._content = document.getElementById('editor-wrapper');
    this._filepath = document.getElementById('file-path');
    this._checkerName = document.getElementById('checker-name');
    this._reviewStatusWrapper =
      document.getElementById('review-status-wrapper');
    this._reviewStatus = document.getElementById('review-status');
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

  navigate : function (report, item) {
    if (!item) {
      var items = this._navigationMenuItems.filter(function (navItem) {
        return navItem.report.reportHash === report.reportHash;
      });

      if (!items.length) return;

      item = items[0].widget;
    }

    this._selectedReport.classList.remove('active');
    this._selectedReport = item;
    this._selectedReport.classList.add('active');
    this.setReport(report);
  },

  _createNavigationMenu : function () {
    var that = this;

    var nav = document.getElementById('report-nav');
    var list = document.createElement('ul');
    this._reports.forEach(function (report) {
      var events = report['events'];
      var lastBugEvent = events[events.length - 1];
      var item = document.createElement('li');

      var severity = document.createElement('i');
      severity.className = 'severity-' + report.severity.toLowerCase();

      item.appendChild(severity);
      item.appendChild(document.createTextNode(lastBugEvent.message));

      item.addEventListener('click', function () {
        that.navigate(report, item);
      })
      list.appendChild(item);
      that._navigationMenuItems.push({ report : report, widget : item });
    });

    if (!this._selectedReport && list.childNodes.length) {
      this._selectedReport = list.childNodes[0];
      this._selectedReport.classList.add('active');
    }

    nav.appendChild(list);
  },

  setReport : function (report) {
    this._currentReport = report;
    var events = report['events'];
    var lastBugEvent = events[events.length - 1];
    this.setCurrentBugEvent(lastBugEvent, events.length - 1);
    this.setCheckerName(report.checkerName);
    this.setReviewStatus(report.reviewStatus);

    window.location.hash = '#reportHash=' + report.reportHash;
  },

  setCurrentBugEvent : function (event, idx) {
    this._currentBugEvent = event;
    this.setSourceFileData(this._files[event.location.file]);
    this.drawBugPath();

    this.jumpTo(event.location.line, 0);
    this.highlightBugEvent(event, idx);
  },

  highlightBugEvent : function (event, idx) {
    this._lineWidgets.forEach(function (widget) {
      var lineIdx = widget.node.getAttribute('idx');
      if (parseInt(lineIdx) === idx) {
        widget.node.classList.add('current');
      }
    });
  },

  setCheckerName : function (checkerName) {
    this._checkerName.innerHTML = checkerName;
  },

  setReviewStatus : function (status) {
    if (status) {
      var className =
        'review-status-' + status.toLowerCase().split(' ').join('-');
      this._reviewStatus.className = "review-status " + className;

      this._reviewStatus.innerHTML = status;
      this._reviewStatusWrapper.style.display = 'block';
    } else {
      this._reviewStatusWrapper.style.display = 'none';
    }
  },

  setSourceFileData : function (file) {
    if (this._sourceFileData && file.id === this._sourceFileData.id) {
      return;
    }

    this._sourceFileData = file;
    this._filepath.innerHTML = file.path;
    this._codeMirror.doc.setValue(file.content);
    this._refresh();
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

  getMessage : function (event, kind) {
    if (kind === 'macro') {
      var name = 'macro expansion' + (event.name ? ': ' + event.name : '');

      return '<span class="tag macro">' + name + '</span>'
        + this.escapeHTML(event.expansion).replace(/(?:\r\n|\r|\n)/g, '<br>');
    } else if (kind === 'note') {
      return '<span class="tag note">note</span>'
        +  this.escapeHTML(event.message).replace(/(?:\r\n|\r|\n)/g, '<br>');
    }
  },

  addExtraPathEvents : function (events, kind) {
    var that = this;

    if (!events) {
      return;
    }

    events.forEach(function (event) {
      if (event.location.file !== that._currentBugEvent.location.file) {
        return;
      }

      var left =
        that._codeMirror.defaultCharWidth() * event.location.col + 'px';

      var element = document.createElement('div');
      element.setAttribute('style', 'margin-left: ' + left);
      element.setAttribute('class', 'check-msg ' + kind);

      var msg = document.createElement('span');
      msg.innerHTML = that.getMessage(event, kind);
      element.appendChild(msg);

      that._lineWidgets.push(that._codeMirror.addLineWidget(
        event.location.line - 1, element));
    });
  },

  drawBugPath : function () {
    var that = this;

    this.clearBubbles();

    this.addExtraPathEvents(this._currentReport.macros, 'macro');
    this.addExtraPathEvents(this._currentReport.notes, 'note');

    // Processing bug path events.
    var currentEvents = this._currentReport.events;
    currentEvents.forEach(function (event, step) {
      if (event.location.file !== that._currentBugEvent.location.file)
        return;

      var left =
        that._codeMirror.defaultCharWidth() * event.location.col + 'px';
      var type = step === currentEvents.length - 1 ? 'error' : 'info';

      var element = document.createElement('div');
      element.setAttribute('style', 'margin-left: ' + left);
      element.setAttribute('class', 'check-msg ' + type);
      element.setAttribute('idx', step);

      var enumeration = document.createElement('span');
      enumeration.setAttribute('class', 'checker-enum ' + type);
      enumeration.innerHTML = step + 1;

      if (currentEvents.length > 1)
        element.appendChild(enumeration);

      var prevBugEvent = step - 1;
      if (step > 0) {
        var prevBug = document.createElement('span');
        prevBug.setAttribute('class', 'arrow left-arrow');
        prevBug.addEventListener('click', function () {
          var event = currentEvents[prevBugEvent];
          that.setCurrentBugEvent(event, prevBugEvent);
        });
        element.appendChild(prevBug);
      }

      var msg = document.createElement('span');
      msg.innerHTML = that.escapeHTML(event.message)
        .replace(/(?:\r\n|\r|\n)/g, '<br>');

      element.appendChild(msg);

      var nextBugEvent = step + 1;
      if (nextBugEvent < currentEvents.length) {
        var nextBug = document.createElement('span');
        nextBug.setAttribute('class', 'arrow right-arrow');
        nextBug.addEventListener('click', function () {
          var event = currentEvents[nextBugEvent];
          that.setCurrentBugEvent(event, nextBugEvent);
        });
        element.appendChild(nextBug);
      }


      that._lineWidgets.push(that._codeMirror.addLineWidget(
        event.location.line - 1, element));
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
