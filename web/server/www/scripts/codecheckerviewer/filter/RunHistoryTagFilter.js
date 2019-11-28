// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter',
  'codechecker/util'],
function (dom, declare, Deferred, SelectFilter, util) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      placeHolder : 'Search for run tags...'
    },

    labelFormatter : function (value, item) {
      var label = value;
      if (item && item.time) {
        label += ' <span class="time">(' + util.prettifyDate(item.time)
          + ')</span>';
      }

      return label;
    },

    getItems : function (opt) {
      var opt = this.initReportFilterOptions(opt);
      opt.reportFilter.runTag = opt.query ? opt.query : null;

      var deferred = new Deferred();
      CC_SERVICE.getRunHistoryTagCounts(opt.runIds, opt.reportFilter,
      opt.cmpData, function (res) {
        deferred.resolve(res.map(function (tag) {
          var tagName = tag.runName + ':' + tag.name;
          return {
            ids   : [tag.id],
            value : tagName,
            count : tag.count,
            time : tag.time
          };
        }));
      }).fail(function (xhr) { util.handleAjaxFailure(xhr); });
      return deferred;
    },

    getIconStyle : function (tagName) {
      return 'color:' + util.strToColor(tagName);
    },

    getIconClass : function () {
      return 'customIcon tag';
    },

    // Returns selected tag id's. If the ids option is set for the filter item
    // we can use it otherwise we get tag id's from the server.
    getTagIds : function () {
      var tagIds =  [];

      for (var key in this.selectedItems) {
        var item = this.selectedItems[key];
        if (item && item.ids) {
          tagIds = tagIds.concat(item.ids);
        } else {
          var index = key.indexOf(':');

          if (index === -1) continue;

          var runName = key.substring(0, index);
          var tagName = key.substring(index + 1);

          var missingTagIds = this.getIdsByTag(runName, tagName);
          if (missingTagIds.length) {
            if (item) item.ids = missingTagIds;
            tagIds = tagIds.concat(missingTagIds);
          }
        }
      }

      return tagIds.length ? tagIds : null;
    },

    // Returns tag id's of the tag name in the specified run. This should call
    // API functions synchronously because other filters should depend on it.
    getIdsByTag : function (runName, tagName) {
      if (!runName || !tagName) return [];

      var runFilter = new CC_OBJECTS.RunFilter();
      runFilter.names = [runName];

      var runIds = [];
      try {
        runIds = CC_SERVICE.getRunData(runFilter, null, 0, null).map(
        function (run) {
          return run.runId;
        });
      } catch (ex) { util.handleThriftException(ex); }

      var runHistoryFilter = new CC_OBJECTS.RunHistoryFilter();
      runHistoryFilter.tagNames = [tagName];

      var runHistoryData = [];
      try {
        runHistoryData =
          CC_SERVICE.getRunHistory(runIds, null, null, runHistoryFilter);
      } catch (ex) { util.handleThriftException(ex); }

      return runHistoryData.map(function (history) { return history.id; });
    }
  });
});
