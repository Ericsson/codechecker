#!/usr/bin/python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Script to check clang and clang-tidy version requirements
to run the tests.
"""


import re
import subprocess
import sys

# clang an clang tidy versions to run the tests
_CLANG_MIN_VERSION = {"major": 11, "minor": 0}
_TIDY_MIN_VERSION = {"major": 11, "minor": 0}


def eprint(*args, **kwargs):
    """ Print to stderr.  """
    print(*args, file=sys.stderr, **kwargs)


def run_cmd(cmd):
    """
    cmd: should be list of strings which contains the command to be
    executed
    Function should handle subprocess errors.
    Return None if execution fails.
    """
    try:
        version = subprocess.check_output(
            cmd, encoding="utf-8", errors="ignore")
        return version
    except subprocess.CalledProcessError as err:
        eprint(err)
        return None


def get_version(output):
    """
    Return the version information from the command output.
    """
    version_regex = r"version \b(?P<major>[0-9]+)(?:\.[0-9]+)?(?:\.[0-9]+)?\b"
    version_matcher = re.compile(version_regex)
    match = version_matcher.search(output)
    if match:
        major = match.groups("major")[0]
        minor = match.groups("minor")[0]
        return (int(major), int(minor))

    eprint("Failed to get version information from the output: \n"
           + output)
    return (None, None)


def check_version(tool_name, got_major_version, expected_major_version):
    """
    Check if the major version is good.
    """
    if got_major_version < expected_major_version["major"]:
        eprint("Expected "+tool_name+" major version is: " +
               str(expected_major_version["major"]))
        eprint("Found "+tool_name+" major version is: " +
               str(got_major_version))
        return False

    return True


def main():
    clang = "clang"
    clang_version_output = run_cmd([clang, "--version"])
    major, _ = get_version(clang_version_output)
    if not major:
        return 1

    valid_version = check_version(clang, major, _CLANG_MIN_VERSION)
    if not valid_version:
        return 1

    tidy = "clang-tidy"
    tidy_version_output = run_cmd([tidy, "--version"])
    major, _ = get_version(tidy_version_output)
    if not major:
        return 1

    valid_version = check_version(tidy, major, _TIDY_MIN_VERSION)
    if not valid_version:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
