import semver from "semver";

export function useVersion() {
  function prettifyCCVersion(version) {
    if (!version) return version;
    return version.split(" ")[0];
  }

  function isNewerOrEqualCCVersion(actual, expected) {
    return semver.gte(semver.coerce(actual), semver.coerce(expected));
  }

  return {
    prettifyCCVersion,
    isNewerOrEqualCCVersion
  };
}