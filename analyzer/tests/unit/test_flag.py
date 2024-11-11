# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Compiler flag checking functions."""


import unittest

from codechecker_analyzer.analyzers import flag


class Flag(unittest.TestCase):
    """Compiler flag related tests."""

    def test_has_flag(self):
        """Test if flag is found in a command."""
        cmd = ["g++", "--target", "x86_64"]
        self.assertTrue(flag.has_flag("--target", cmd))
        self.assertTrue(flag.has_flag("x86_64", cmd))

    def test_missing_flag(self):
        """Test if flag was not found in a command."""
        cmd = ["g++", "--target", "x86_64"]
        self.assertFalse(flag.has_flag("-std", cmd))
