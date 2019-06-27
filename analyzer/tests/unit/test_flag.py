# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Compiler flag checking functions."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

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
