# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Parse the 'clang-tidy --version' command output."""

import re
import subprocess

from codechecker_analyzer.analyzers.version_info import VersionInfo


class TidyVersionInfoParser(object):
    """
    Parse the version information for clang-tidy binary.
    """

    def __init__(self):
        self.clang_version_pattern = (
            r"(?P<vendor>LLVM) version (?P<major_version>[0-9]+)"
            r"\.(?P<minor_version>[0-9]+)\.(?P<patch_version>[0-9]+)")

    def parse(self, version_string):
        """Try to parse the version string using the predefined patterns."""
        version_match = re.search(self.clang_version_pattern, version_string)

        if not version_match:
            return False

        return VersionInfo(
            major_version=version_match.group('major_version'),
            minor_version=version_match.group('minor_version'),
            patch_version=version_match.group('patch_version'),
            vendor=version_match.group('vendor'),
            cmd_output=version_string)


def get(clang_tidy_binary, env=None):
    """Get and parse the version information from given clang-tidy binary

    Should return False for getting the version
    information not from a clang-tidy binary.
    """
    clang_tidy_version_output = subprocess.check_output(
        [clang_tidy_binary, '--version'],
        env=env,
        encoding="utf-8",
        errors="ignore")
    version_parser = TidyVersionInfoParser()
    version_info = version_parser.parse(clang_tidy_version_output)
    return version_info
