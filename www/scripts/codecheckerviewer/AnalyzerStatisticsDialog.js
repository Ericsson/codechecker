// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dijit/Dialog'],
function (declare, dom, Dialog) {
  return declare(Dialog, {
    title : 'Analyzer statistics',
    style : 'max-width: 75%; min-width: 50%;',

    show : function (stats) {
      var ul = dom.create('ul', { class: 'analyzer-statistics' });

      Object.keys(stats).forEach(function (analyzer) {
        var item = dom.create('li', null, ul);
        dom.create('h3', { innerHTML : analyzer }, item);

        var items = dom.create('ul', { class : 'items' }, item);

        // Version information
        if (stats[analyzer].version) {
          var li = dom.create('li', {
            class : 'version',
            title : 'Version information.'
          }, items);

          dom.create('b', { innerHTML : 'Version: ' }, li);

          var versionList = dom.create('ul', { class : 'version' }, li);
          stats[analyzer].version.trim().split('\n').forEach(function (item) {
            dom.create('li', { innerHTML : item.trim() }, versionList);
          });
        }

        // Successfully analyzed files.
        var successLi = dom.create('li', {
          class : 'successful',
          title : 'Number of successfully analyzed files.'
        }, items);

        dom.create('b', {
          innerHTML : 'Number of successfully analyzed files '
                    + '(<i class="customIcon check"></i>): '
        }, successLi);

        dom.create('span', {
          class : 'num',
          innerHTML : stats[analyzer].successful
        }, successLi);

        // Files which failed to analyze.
        var failureLi = dom.create('li', {
          class : 'failed',
          title : 'Number of files which failed to analyze.'
        }, items);

        dom.create('b', {
          innerHTML : 'Number of files which failed to analyze '
                    + '(<i class="customIcon remove"></i>): '
        }, failureLi);

        dom.create('span', {
          class : 'num',
          innerHTML : stats[analyzer].failed
        }, failureLi);

        if (stats[analyzer].failed) {
          var failedFiles = dom.create('ul');
          stats[analyzer].failedFilePaths.forEach(function (file) {
            dom.create('li', { innerHTML : file }, failedFiles);
          });

          dom.create('li', {
            innerHTML : '<b>Files which failed to analyze</b>: '
                      + failedFiles.outerHTML
          }, items);
        }
      });

      this.set('content', ul);
      this.resize();
      this.inherited(arguments);
    }
  });
});
