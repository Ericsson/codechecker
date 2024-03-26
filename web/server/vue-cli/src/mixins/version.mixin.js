import semver from "semver";

export default {
  methods: {
    prettifyCCVersion(version) {
      if (!version) return version;
      return version.split(" ")[0];
    },

    isNewerOrEqualCCVersion(actual, expected) {
      return semver.gte(semver.coerce(actual), semver.coerce(expected));
    }
  }
};
