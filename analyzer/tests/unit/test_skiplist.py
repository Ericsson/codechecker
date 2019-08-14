# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Skip list tests."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

from codechecker_analyzer.skiplist import SkipListHandler


class SkipList(unittest.TestCase):
    """Skip list related tests."""

    @classmethod
    def setup_class(cls):
        """Initialize a checkers list for the tests.

        Order of the lines in the skip file matter!
        Go from more specific to more global rules like:
        +*/3pp_other/lib/not_to_skip.cpp
        -*/3pp_other/*
        """
        cls._skip_list = \
            """
            -/skip/all/source/in/directory*
            -/do/not/check/this.file
            +/dir/check.this.file
            -/dir/*
            -*/3pp/to_skip/
            +*/3pp/not_to_skip/
            +*/3pp_other/lib/not_to_skip.cpp
            -*/3pp_other/*
            """

    def test_skip_absolute_path(self):
        """Skip rule is an absolute path in the file."""
        slh = SkipListHandler(self._skip_list)

        self.assertTrue(slh.should_skip(
            "/skip/all/source/in/directory/lib1.cpp"))
        self.assertTrue(slh.should_skip(
            "/skip/all/source/in/directory/lib1.h"))
        self.assertTrue(slh.should_skip(
            "/skip/all/source/in/directory/lib2.cpp"))
        self.assertTrue(slh.should_skip("/do/not/check/this.file"))
        self.assertTrue(slh.should_skip("/dir/main.cpp"))
        self.assertTrue(slh.should_skip("/dir/lib.cpp"))
        self.assertTrue(slh.should_skip("/dir/lib2/lib2.cpp"))

        self.assertFalse(slh.should_skip("/dir/check.this.file"))

    def test_skip_relative_path(self):
        """Skip rule is not an absolute path in the skip file."""
        slh = SkipListHandler(self._skip_list)

        self.assertTrue(slh.should_skip("/lib/3pp/to_skip/3pp.cpp"))
        self.assertTrue(slh.should_skip("/lib/3pp_other/lib/skip.cpp"))
        self.assertTrue(slh.should_skip("/lib/3pp_other/skip_other.cpp"))

        self.assertFalse(slh.should_skip(
            "/lib/3pp_other/lib/not_to_skip.cpp"))
