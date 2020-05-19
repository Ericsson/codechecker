// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter',
  'codechecker/util'],
function (declare, Deferred, SelectFilter, util) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      serverSide : true,
      regex : true,
      regexLabel : 'Filter by wildcard pattern (e.g.: myrun*:mytag*, mytag*): ',
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
      opt.reportFilter.runTag = opt.query ? this.getTagIds(opt.query) : null;

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
    getTagIds : function (runWithTagNames) {
      if (runWithTagNames === undefined)
      runWithTagNames = Object.keys(this.selectedItems);

      var tagIds =  [];

      var that = this;
      runWithTagNames.forEach(function (runWithTagName) {
        var item = that.selectedItems[runWithTagName];
        if (item && item.ids) {
          tagIds = tagIds.concat(item.ids);
        } else {
          var index = runWithTagName.indexOf(':');

          var runName, tagName;
          if (index !== -1) {
            runName = runWithTagName.substring(0, index);
            tagName = runWithTagName.substring(index + 1);
          } else {
            tagName = runWithTagName;
          }

          var missingTagIds = that.getIdsByTag(runName, tagName);
          if (missingTagIds.length) {
            if (item) item.ids = missingTagIds;
            tagIds = tagIds.concat(missingTagIds);
          }
        }
      });

      return tagIds.length ? tagIds : null;
    },

    // Returns tag id's of the tag name in the specified run. This should call
    // API functions synchronously because other filters should depend on it.
    // If no run name is given we will get tag id's only by tag name.
    getIdsByTag : function (runName, tagName) {
      if (!tagName) return [];

      var runIds = null;
      if (runName) {
        var runFilter = new CC_OBJECTS.RunFilter();
        runFilter.names = [runName];

        try {
          runIds = CC_SERVICE.getRunData(runFilter, null, 0, null).map(
          function (run) {
            return run.runId;
          });
        } catch (ex) { util.handleThriftException(ex); }
      }

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
