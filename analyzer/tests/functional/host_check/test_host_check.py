# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Tests for analyzer features.
"""


import unittest

import codechecker_analyzer.host_check as hc


class Test_has_analyzer_option(unittest.TestCase):
    def test_existing_option(self):
        self.assertEqual(
            hc.has_analyzer_option("clang",
                                   ["-analyzer-display-progress"]),
            True)

    def test_non_existing_option(self):
        self.assertEqual(
            hc.has_analyzer_option("clang",
                                   ["-non-existent-feature"]),
            False)

    def test_non_existent_option_binary(self):
        self.assertEqual(
            hc.has_analyzer_option("non-existent-binary-Yg4pEna5P7",
                                   [""]),
            False)

    def test_non_existing_congif_option(self):
        self.assertEqual(
            hc.has_analyzer_config_option("clang",
                                          "non-existent-config-option"),
            False)

    def test_non_existent_config_option_binary(self):
        with self.assertRaises(OSError):
            hc.has_analyzer_config_option("non-existent-binary-Yg4pEna5P7", "")
