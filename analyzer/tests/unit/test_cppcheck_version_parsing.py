# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test Cppcheck version parsing. """


from semver.version import Version
import unittest

from codechecker_analyzer.analyzers.cppcheck.analyzer import parse_version


class CppcheckVersionTest(unittest.TestCase):
    """
    Test the parsing of various possible version strings, which cppcheck
    binaries can produce.
    """

    def test_cppcheck_version(self):
        self.assertEqual(
            parse_version('Cppcheck 1.2.3'),
            Version(1, 2, 3))
        self.assertEqual(
            parse_version('Cppcheck Premium 1.2.3'),
            Version(1, 2, 3))
        self.assertEqual(
            parse_version('Cppcheck 2.7'),
            Version(2, 7, 0))
