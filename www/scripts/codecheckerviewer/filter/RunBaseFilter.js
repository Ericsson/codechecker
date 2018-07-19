// -------------------------------------------------------------------------
//                     The CodeChecker Infrastructure
//   This file is distributed under the University of Illinois Open Source
//   License. See LICENSE.TXT for details.
// -------------------------------------------------------------------------

define([
  'dojo/dom-construct',
  'dojo/_base/declare',
  'dojo/Deferred',
  'codechecker/filter/SelectFilter'],
function (dom, declare, Deferred, SelectFilter) {
  return declare(SelectFilter, {
    search : {
      enable : true,
      serverSide : true,
      regex : true,
      regexLabel : 'Filter by wildcard pattern (e.g.: myrun*): ',
      placeHolder : 'Search for run names (e.g.: myrun*)...'
    },

    getItems : function (opt) {
      opt = this.initReportFilterOptions(opt);
      opt.reportFilter.runName = opt.query ? opt.query : null;

      var deferred = new Deferred();
      CC_SERVICE.getRunReportCounts(null, opt.reportFilter, opt.limit,
      opt.offset, function (res) {
        deferred.resolve(res.map(function (run) {
          return {
            ids : [run.runId],
            value : run.name,
            count : run.reportCount
          };
        }));
      });
      return deferred;
    },

    // Returns selected run id's. If the ids option is set for the filter item
    // we can use it otherwise we get run id's from the server.
    getRunIds : function () {
      var runIds =  [];

      for (var key in this.selectedItems) {
        var item = this.selectedItems[key];
        if (item && item.ids) {
          runIds = runIds.concat(item.ids);
        } else {
          var missingRunIds = this.getIdsByRunName(key);

          if (item)
            item.ids = missingRunIds;

          if (missingRunIds.length)
            runIds = runIds.concat(missingRunIds);
        }
      }

      return runIds.length ? runIds : null;
    },

    // Returns id's of runs by using a run name filter.
    getIdsByRunName : function (runName) {
      var runFilter = new CC_OBJECTS.RunFilter();
      runFilter.names = [runName];

      var runData = CC_SERVICE.getRunData(runFilter);
      return runData.map(function (run) { return run.runId; });
    },

    getRunNames : function () {
      return Object.keys(this.selectedItems);
    }
  });
});
