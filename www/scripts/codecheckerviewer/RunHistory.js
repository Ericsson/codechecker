// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/dom-construct',
  'dojo/topic',
  'dijit/layout/ContentPane',
  'codechecker/hashHelper',
  'codechecker/util'],
function (declare, dom, topic, ContentPane, hashHelper, util) {

  return declare(ContentPane, {
    constructor : function (args) {
      dojo.safeMixin(this, args);

      this.runId = this.runData ? this.runData.runId : null;
    },

    postCreate : function () {
      this.inherited(arguments);

      var that = this;

      // Get histories for the actual run
      var runIds = this.runId ? [this.runId] : null;
      var historyData = CC_SERVICE.getRunHistory(
        runIds, CC_OBJECTS.MAX_QUERY_SIZE, 0);

      var historyGroupByDate = {};
      historyData.forEach(function (data) {
        var date = new Date(data.time.replace(/ /g,'T'));
        var groupDate = date.getDate() + ' '
          + util.getMonthName(date.getMonth()) + ', '
          + date.getFullYear();

        if (!historyGroupByDate[groupDate])
          historyGroupByDate[groupDate] = [];

        historyGroupByDate[groupDate].push(data);
      });

      var filter = this.bugFilterView;
      var dateFilter = filter._detectionDateFilter;
      var dsFilter = filter._detectionStatusFilter;
      var runFilter = filter._runNameFilter;

      Object.keys(historyGroupByDate).forEach(function (key) {
        var group = dom.create('div', { class : 'history-group' }, that.domNode);
        dom.create('div', { class : 'header', innerHTML : key }, group);
        var content = dom.create('div', { class : 'content' }, group);

        historyGroupByDate[key].forEach(function (data) {
          var date = new Date(data.time.replace(/ /g,'T'));
          var time = util.formatDateAMPM(date);

          var history = dom.create('div', {
            class : 'history',
            onclick : function () {
              that.bugFilterView.clearAll();

              if (runFilter)
                runFilter.select(data.runName);

              if (!data.versionTag) {
                [
                  CC_OBJECTS.DetectionStatus.NEW,
                  CC_OBJECTS.DetectionStatus.UNRESOLVED,
                  CC_OBJECTS.DetectionStatus.REOPENED
                ].forEach(function (status) {
                  dsFilter.select(dsFilter.stateConverter(status));
                });
                dateFilter.initFixedDateInterval(that._formatDate(date));
              } else {
                filter._runHistoryTagFilter.select(
                  data.runName + ":" + data.versionTag);
              }

              that.bugFilterView.notifyAll();
              hashHelper.setStateValues({subtab : null});
            }
          }, content);

          dom.create('span', { class : 'time', innerHTML : time }, history);

          var runNameWrapper = dom.create('span', { class : 'run-name-wrapper', title: 'Run name'}, history);
          dom.create('span', { class : 'customIcon run-name' }, runNameWrapper);
          dom.create('span', { class : 'run-name', innerHTML : data.runName }, runNameWrapper);

          if (data.versionTag) {
            var runTag = util.createRunTag(data.runName, data.versionTag);
            dom.place(runTag, history);
          }

          var userWrapper = dom.create('span', {class : 'user-wrapper', title: 'User name' }, history);
          dom.create('span', { class : 'customIcon user' }, userWrapper);
          dom.create('span', { class : 'user', innerHTML : data.user }, userWrapper);
        })
      });
    },


    _formatDate : function (date) {
      var mm = date.getMonth() + 1; // getMonth() is zero-based
      var dd = date.getDate();

      return [date.getFullYear(),
              (mm > 9 ? '' : '0') + mm,
              (dd > 9 ? '' : '0') + dd
             ].join('-') + ' ' +
             [date.getHours(),
              date.getMinutes(),
              date.getSeconds() + (date.getMilliseconds() > 0 ? 1 : 0)
             ].join(':');
    }
  });
});
