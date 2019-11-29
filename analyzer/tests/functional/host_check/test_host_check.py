# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Tests for analyzer features.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

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
