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
  'codechecker/util'],
function (declare, dom, topic, ContentPane, util) {

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

      var dateFilter = that.bugFilterView._detectionDateFilter;
      var detectionStatusFilter =
        that.bugFilterView._detectionStatusFilter;

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
              var state = that.bugFilterView.clearAll();
              state.run = [data.runName];
              state.subtab = null;

              if (!data.versionTag) {
                state[detectionStatusFilter.class] = [
                  detectionStatusFilter.stateConverter(CC_OBJECTS.DetectionStatus.NEW),
                  detectionStatusFilter.stateConverter(CC_OBJECTS.DetectionStatus.UNRESOLVED),
                  detectionStatusFilter.stateConverter(CC_OBJECTS.DetectionStatus.REOPENED)];
                state[dateFilter._toDate.class] = that._formatDate(date);
              } else {
                state['run-history-tag'] = data.runName + ':' + data.versionTag;
              }

              topic.publish('filterchange', {
                parent : that.bugOverView,
                changed : state
              });
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
