// -------------------------------------------------------------------------
//  Part of the CodeChecker project, under the Apache License v2.0 with
//  LLVM Exceptions. See LICENSE for license information.
//  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
// -------------------------------------------------------------------------

var Statistics = {

  init : function () {
    var checker_statistics = document.getElementById('checker-statistics');

    for (var checker_data of checker_statistics_data) {
      var row = document.createElement('tr');

      var checker_name = document.createElement('td');
      checker_name.innerHTML = checker_data['checker_name'];
      row.appendChild(checker_name);

      var severity = document.createElement('td');
      severity.setAttribute('class', 'severity');
      severity.setAttribute('severity', checker_data['severity']);
      var severity_i = document.createElement('i');
      severity_i.setAttribute('class', 'severity-' + checker_data['severity']);
      severity_i.setAttribute('title', checker_data['severity']);
      severity.appendChild(severity_i);
      row.appendChild(severity);

      var value = document.createElement('td');
      value.innerHTML = checker_data['value'];
      row.appendChild(value);

      checker_statistics.appendChild(row);
    }

    var severity_statistics = document.getElementById('severity-statistics');

    for (var severity_data of severity_statistics_data) {
      var row = document.createElement('tr');

      var severity = document.createElement('td');
      severity.setAttribute('class', 'severity');
      severity.setAttribute('severity', severity_data['severity']);
      var severity_i = document.createElement('i');
      severity_i.setAttribute(
        'class', 'severity-' + severity_data['severity']);
      severity_i.setAttribute('title', severity_data['severity']);
      severity.appendChild(severity_i);
      row.appendChild(severity);

      var value = document.createElement('td');
      value.innerHTML = severity_data['value'];
      row.appendChild(value);

      severity_statistics.appendChild(row);
    }
  }

};