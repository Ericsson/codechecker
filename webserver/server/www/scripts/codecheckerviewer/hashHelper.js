define([
  'dojo/hash',
  'dojo/io-query',
  'dojo/topic',
  'codechecker/util'],
function (hash, ioQuery, topic, util) {
  /**
   * URL state object
   */
  var state = {};

  var hashHelper = {
   /**
    * This function pushes the currently stored state to the browser history.
    * During the update process, the "hashSetProgress" variable of the
    * urlHandler object is set to true. This signs that the url update in the
    * browser was done by urlHandler, not by the "browser back" or "browser
    * forward" buttons.
    */
    updateUrl : function () {
      this.hashSetProgress = true;

      hash(ioQuery.objectToQuery(state));

      var that = this;

      // In Firefox the following will be executed before hashchange event if
      // the timeout value is zero. For this reason we set it to a higher
      // value.
      setTimeout(function () { that.hashSetProgress = false; }, 100);
    },

    /**
     * Clear the state and updates the URL.
     */
    clear : function () {
      state = {};
      this.updateUrl();
    },

    /**
     * Return the current state
     */
    getValues : function () {
      return ioQuery.queryToObject(hash());
    },

    /**
     * This function returns the whole current value associated with the given
     * key in the URL. If the key is not given, returns the whole state as a
     * JavaScript object is returned.
     */
    getState : function (key) {
      return key === undefined ? state : state[key];
    },

    /**
     * Modifies the given value(s), the rest of the current state is untouched.
     * For example setting the key1-value1 and key2-value2 pairs means that the
     * url will contain #key1=value1&key2=value2 hash.
     * @param obj {Object} - Key-value pairs.
     */
    setStateValues : function (obj, preventUpdateUrl) {
      var changed = false;

      for (var key in obj) {
        var value = obj[key];

        if (state[key] === value)
          continue;

        if (state[key] === undefined && value === null)
          continue;

        if (value === null) {
          delete state[key];
          changed = true;
          continue;
        }

        state[key] = value;
        changed = true;
      }

      if (changed && !preventUpdateUrl)
        this.updateUrl();
    },

    resetStateValues : function (obj) {
      state = {};
      this.setStateValues(obj, false);
    },

    /**
     * Modifies the given value of the state and updates the url.
     * @see setStateValues
     */
    setStateValue : function (key, value, preventUpdateUrl) {
      var state = {};
      state[key] = value;

      this.setStateValues(state, preventUpdateUrl);
    }
  };

  //--- Init state by the current URL ---//

  state = hashHelper.getValues();

  //--- Remove the same url values. Eg.: foo=1&foo=1 ---//

  for (var key in state)
    if (state[key] instanceof Array)
      state[key] = util.arrayUnique(state[key]);

  hashHelper.updateUrl();

  /**
   * When "browser back" or "browser forward" button is pressed, then the global
   * state object is set to the changed url hash, so that the state variable and
   * the current url be synchronized.
   */
  topic.subscribe('/dojo/hashchange', function (url) {
    if (hashHelper.hashSetProgress) return;

    state = hashHelper.getValues();
  });

  return hashHelper;
});
