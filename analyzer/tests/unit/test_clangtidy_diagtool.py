# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test the lookup of the diagtool binary next to clang-tidy.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from semver.version import Version

from codechecker_analyzer.analyzers.clangtidy import analyzer


class GetDiagtoolBinTest(unittest.TestCase):
    """
    Test that get_diagtool_bin() uses the platform specific binary names.
    """

    def _lookup(self, platform, existing, version=None):
        """
        Create the 'existing' files next to a fake clang-tidy and return the
        result of get_diagtool_bin() as a file name (or None).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp).resolve()
            for name in existing:
                (tmp / name).touch()

            context = mock.Mock()
            context.analyzer_binaries = {
                analyzer.ClangTidy.ANALYZER_NAME: str(tmp / 'clang-tidy')}

            with mock.patch.object(analyzer.analyzer_context, 'get_context',
                                   return_value=context), \
                    mock.patch.object(analyzer.ClangTidy,
                                      'get_binary_version',
                                      return_value=version), \
                    mock.patch.object(analyzer.sys, 'platform', platform):
                result = analyzer.get_diagtool_bin()

            return result.name if result else None

    def test_unix(self):
        self.assertEqual(
            self._lookup('linux', ['diagtool']), 'diagtool')

    def test_windows(self):
        self.assertEqual(
            self._lookup('win32', ['diagtool.exe']), 'diagtool.exe')

    def test_windows_ignores_extensionless(self):
        self.assertIsNone(self._lookup('win32', ['diagtool']))

    def test_unix_versioned(self):
        self.assertEqual(
            self._lookup('linux', ['diagtool-14'], Version(14, 0, 0)),
            'diagtool-14')

    def test_windows_versioned(self):
        self.assertEqual(
            self._lookup('win32', ['diagtool-14.exe'], Version(14, 0, 0)),
            'diagtool-14.exe')

    def test_not_found(self):
        self.assertIsNone(self._lookup('linux', [], Version(14, 0, 0)))
