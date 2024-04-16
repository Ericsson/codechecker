// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

var BugList = {

  _urlHash : function () {
    var state = {};
    window.location.hash.substring(1).split('&').forEach(function (s) {
      var parts = s.split('=');
      state[parts[0]] = parts[1];
    });
    return state;
  },

  _cmp3 : function (a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  },

  initTableSort : function () {
    var that = this;

    var table = document.getElementById('report-list-table');
    table.querySelectorAll('th').forEach(function (column) {
      column.addEventListener('click', function () {
        var state = that._urlHash();

        var asc = state.sort === column.id
          ? !parseInt(state.asc)
          : !!parseInt(state.asc);

        that.sort(column.id, asc);
        that.load();
      });
      column.classList.add('sortable');
    });
  },

  initBugPathLength : function () {
    var that = this;

    document.querySelectorAll('.bug-path-length').forEach(
    function (widget) {
      widget.style.backgroundColor =
        that.generateRedGreenGradientColor(widget.innerHTML, 20, 0.5);
    });
  },

  initByUrl : function () {
    var state = this._urlHash();
    var column = state['sort'] ? state['sort'] : 'file-path';
    var asc = state['asc'] ? !!parseInt(state['asc']) : true;
    this.initTableSort();
    this.sort(column, asc);
    this.load();
  },

  generateRedGreenGradientColor : function (value, max, opacity) {
    var red   = (255 * value) / max;
    var green = (255 * (max - value)) / max;
    var blue  = 0;
    return 'rgba(' + parseInt(red) + ',' + parseInt(green) + ',' + blue
      + ',' + opacity + ')';
  },

  sort : function (columnId, asc) {
    var that = this;

    var severities = ['STYLE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

    function compare(a, b) {
      var result;

      if (columnId == 'file-path')
        result = that._cmp3(
          [a['file-path'], a['line']],
          [b['file-path'], b['line']]);

      if (columnId == 'severity')
        result = that._cmp3(
          severities.indexOf(a['severity']),
          severities.indexOf(b['severity']));

      result = that._cmp3(a[columnId], b[columnId]);

      return asc ? result : -result;
    }

    reports.sort(compare);
    window.location.hash = '#sort=' + columnId + '&asc=' + (asc ? 1 : 0);
  },

  buildRow : function (data, id) {
    let row = document.createElement('tr');

    let id_col = document.createElement('td');
    id_col.appendChild(document.createTextNode(id));
    row.appendChild(id_col);

    let file_col = document.createElement('td');
    let file_col_a = document.createElement('a');
    file_col_a.setAttribute(
      'href', data.link + '#reportHash=' + data['report-hash']);
    file_col_a.innerHTML = data['file-path'] + ' @ Line&nbsp;' + data.line;
    file_col.appendChild(file_col_a);
    row.appendChild(file_col);

    let severity_col = document.createElement('td');
    severity_col.setAttribute('class', 'severity');
    let severity_col_i = document.createElement('i');
    severity_col_i.setAttribute(
      'class', 'severity-' + data.severity.toLowerCase());
    severity_col_i.setAttribute('title', data.severity);
    severity_col.appendChild(severity_col_i);
    row.appendChild(severity_col);

    let checker_col = document.createElement('td');
    let checker_col_a = document.createElement('a');
    checker_col_a.setAttribute('href', data['checker-url']);
    checker_col_a.setAttribute('target', '_blank');
    checker_col_a.appendChild(
      document.createTextNode(data['checker-name']));
    checker_col.appendChild(checker_col_a);
    row.appendChild(checker_col);

    let message_col = document.createElement('td');
    message_col.appendChild(document.createTextNode(data.message));
    row.appendChild(message_col);

    let length_col = document.createElement('td');
    length_col.setAttribute('class', 'bug-path-length');
    length_col.appendChild(document.createTextNode(data['bug-path-length']));
    row.appendChild(length_col);

    let review_col = document.createElement('td');
    review_col.appendChild(document.createTextNode(data['review-status']));
    row.appendChild(review_col);

    return row;
  },

  loadTable : function (pageNo, pageSize) {
    var startIdx = (pageNo - 1) * pageSize;
    var endIdx = Math.min(startIdx + pageSize, reports.length);

    var report_list = document.getElementById('report-list');
    report_list.innerHTML = '';

    for (var i = startIdx; i < endIdx; ++i)
      report_list.appendChild(this.buildRow(reports[i], i + 1));

    this.initBugPathLength();
  },

  loadPageNumber : function () {
    var pageSize = parseInt(document.getElementById('page-size').value);
    var pageCount = Math.ceil(reports.length / pageSize);

    var pageNumber = document.getElementById('page-number');
    pageNumber.innerHTML = '';

    for (var i = 1; i <= pageCount; ++i) {
      var option = document.createElement('option');
      option.setAttribute('value', i);
      option.innerHTML = i;
      pageNumber.appendChild(option);
    }
  },

  selectPage : function (pageNumber) {
    var pageSize = parseInt(document.getElementById('page-size').value);
    this.loadTable(pageNumber, pageSize);
  },

  prevPage : function () {
    var pageNumber = document.getElementById('page-number');
    pageNumber.value = Math.max(parseInt(pageNumber.value) - 1, 1);
    this.selectPage(pageNumber.value);
  },

  nextPage : function () {
    var pageNumber = document.getElementById('page-number');
    pageNumber.value = Math.min(
      parseInt(pageNumber.value) + 1,
      pageNumber.children.length);
    this.selectPage(pageNumber.value);
  },

  load : function () {
    var pageSize = parseInt(document.getElementById('page-size').value);

    this.loadPageNumber();
    this.loadTable(1, pageSize);
  }
};
