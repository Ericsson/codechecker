define([
  'dojo/hash',
  'dojo/io-query'],
function (hash, ioQuery) {
  var values = {};

  return {
    setRun : function (runId) {
      delete values.baseline;
      delete values.newcheck;
      delete values.report;
      values.run = runId;
      hash(ioQuery.objectToQuery(values));
    },

    setDiff : function (baselineId, newcheckId) {
      delete values.run;
      delete values.report;
      values.baseline = baselineId;
      values.newcheck = newcheckId;
      hash(ioQuery.objectToQuery(values));
    },

    setReport : function (reportId) {
      values.report = reportId;
      hash(ioQuery.objectToQuery(values));
    },

    removeReport : function (reportId) {
      if(values.report)
        delete values.report;
      hash(ioQuery.objectToQuery(values));
    },

    setFilter : function (filterGroup) {
      var filters = filterGroup.getChildren().map(function (filter) {
        return filter.getValues();
      });
      values.filters = JSON.stringify(filters);
      hash(ioQuery.objectToQuery(values));
    },

    clear : function () {
      values = {};
      hash(ioQuery.objectToQuery(values));
    },

    getValues : function () {
      values = ioQuery.queryToObject(hash());
      if ( values.filters ){
        var text = decodeURIComponent(values.filters);
        values.filters = JSON.parse(text);
      }
      return values
    }
  };
});
