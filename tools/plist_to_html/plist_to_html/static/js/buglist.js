// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

var BugList = {

  init : function () {
    this.initTableSort();
    this.initBugPathLength();
    this.initByUrl();
  },

  initTableSort : function () {
    var that = this;

    var table = document.getElementById('report-list');
    table.querySelectorAll('th').forEach(function (column) {
      if (that.canSort(column.id)) {
        column.addEventListener('click', function () {
          that.sort(column.id);
        });
        column.classList.add('sortable');
      }
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
    var state = {};
    window.location.hash.substr(1).split('&').forEach(function (s) {
      var parts = s.split('=');
      state[parts[0]] = parts[1];
    });

    var column = state['sort'] ? state['sort'] : 'file-path';
    var asc = state['asc'] ? !!parseInt(state['asc']) : true;
    this.sort(column, asc);
  },

  generateRedGreenGradientColor : function (value, max, opacity) {
    var red   = (255 * value) / max;
    var green = (255 * (max - value)) / max;
    var blue  = 0;
    return 'rgba(' + parseInt(red) + ',' + parseInt(green) + ',' + blue
      + ',' + opacity + ')';
  },

  canSort : function (columnId) {
    return columnId === 'report-id' ||
           columnId === 'file-path' ||
           columnId === 'severity' ||
           columnId === 'checker-name' ||
           columnId === 'message' ||
           columnId === 'bug-path-length' ||
           columnId === 'review-status';
  },

  compare : function (columnId, a, b, asc) {
    switch (columnId) {
      case 'report-id':
      case 'bug-path-length':
        return asc
          ? parseInt(a.innerHTML) > parseInt(b.innerHTML)
          : parseInt(a.innerHTML) < parseInt(b.innerHTML);

      case 'file-path':
        var fileA = a.getAttribute('file');
        var fileB = b.getAttribute('file');
        var lineA = parseInt(a.getAttribute('line'));
        var lineB = parseInt(b.getAttribute('line'));

        if (asc) {
          if (fileA > fileB) {
            return true;
          } else if (fileA === fileB) {
            return lineA > lineB ? true : false;
          } else {
            return false;
          }
        } else {
          if (fileA < fileB) {
            return true;
          } else if (fileA === fileB) {
            return lineA < lineB ? true : false;
          } else {
            return false;
          }
        }

      case 'severity':
        return asc
          ? a.getAttribute('severity') > b.getAttribute('severity')
          : a.getAttribute('severity') < b.getAttribute('severity');

      default:
        return asc
          ? a.innerHTML.toLowerCase() > b.innerHTML.toLowerCase()
          : a.innerHTML.toLowerCase() < b.innerHTML.toLowerCase();
    }
  },

  sort : function (columnId, asc) {
    var rows = null,
        switching = true,
        i, j, x, y, minIdx;

    var table = document.getElementById('report-list');
    var column = document.getElementById(columnId);
    var cellIndex = column.cellIndex;

    if (asc === undefined) {
      asc = column.getAttribute('sort') === 'desc' ? false : true;
    }

    var n = table.rows.length;
    for (i = 1; i < n - 1; i++)
    {
      minIdx = i;
      for (j = i + 1; j < n; j++) {
        x = table.rows[minIdx].getElementsByTagName('td')[cellIndex];
        y = table.rows[j].getElementsByTagName('td')[cellIndex];
        if (this.compare(columnId, x, y, asc)) {
          minIdx = j;
        }
      }

      if (minIdx !== i) {
        table.rows[i].parentNode.insertBefore(
          table.rows[minIdx], table.rows[i]);
      }
    }

    table.querySelectorAll('th').forEach(function (column) {
      column.removeAttribute('sort');
      column.classList.remove('active');
    });

    column.classList.add('active');
    column.setAttribute('sort', asc ? 'desc' : 'asc');
    window.location.hash = '#sort=' + columnId + '&asc=' + (asc ? 1 : 0);
  }
};
