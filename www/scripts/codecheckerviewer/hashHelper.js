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
     * Clear the state and updates the URL.
     */
    clear : function () {
      state = {};
      hash(ioQuery.objectToQuery(state));
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

      for (key in obj) {
        var value = obj[key];

        if (state[key] === value)
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
        hash(ioQuery.objectToQuery(state));
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
      this.setStateValues({ [key] : value }, preventUpdateUrl);
    }
  };

  //--- Init state by the current URL ---//

  state = hashHelper.getValues();

  //--- Remove the same url values. Eg.: foo=1&foo=1 ---//

  for (var key in state)
    if (state[key] instanceof Array)
      state[key] = util.arrayUnique(state[key]);

  hash(ioQuery.objectToQuery(state));

  /**
   * When "browser back" or "browser forward" button is pressed, then the global
   * state object is set to the changed url hash, so that the state variable and
   * the current url be synchronized.
   */
  topic.subscribe('/dojo/hashchange', function (url) {
    state = hashHelper.getValues();
  });

  return hashHelper;
});
