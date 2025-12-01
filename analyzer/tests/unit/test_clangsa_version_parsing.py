# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test Clang version parsing. """


from semver.version import Version
import unittest

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA


class ClangsaVersionTest(unittest.TestCase):
    """
    Test the parsing of various possible version strings, which clang
    binaries can produce.
    """

    def test_clangsa_version(self):
        self.assertEqual(
            ClangSA.parse_version('18.1.3'),
            Version(18, 1, 3))
        self.assertEqual(
            ClangSA.parse_version('22.0.0git'),
            Version(22, 0, 0))
