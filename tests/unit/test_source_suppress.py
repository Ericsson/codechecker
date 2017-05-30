# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Tests for suppressing by comment in source file."""

import os
import unittest

from libcodechecker.suppress_handler import SourceSuppressHandler


class SourceSuppressTestCase(unittest.TestCase):
    """Tests for suppressing by comment in source file."""

    @classmethod
    def setup_class(cls):
        """Initialize test source file references."""
        cls.__test_src_dir = os.path.join(
            os.path.dirname(__file__), 'source_suppress_test_files')

        cls.__tmp_srcfile_1 = os.path.join(cls.__test_src_dir, 'test_file_1')
        cls.__tmp_srcfile_2 = os.path.join(cls.__test_src_dir, 'test_file_2')

    def test_suppress_first_line(self):
        """Bug is reported for the first line."""
        test_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                             3,
                                             "0",
                                             "")
        res = test_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(test_handler.suppressed_checkers(), set())
        self.assertIsNone(test_handler.suppress_comment())

    def test_no_comment(self):
        """There is no comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           9,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(sp_handler.suppressed_checkers(), set())
        self.assertIsNone(sp_handler.suppress_comment())

    def test_no_suppress_comment(self):
        """There is suppress comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           16,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), {'all'})
        self.assertEqual(sp_handler.suppress_comment(), 'some comment')

    def test_multi_liner_all(self):
        """There is suppress comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           23,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), {'all'})
        self.assertEqual(sp_handler.suppress_comment(), 'some long comment')

    def test_one_liner_all(self):
        """There is suppress comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           29,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(
            sp_handler.suppressed_checkers(), {'my_checker_1', 'my_checker_2'})
        self.assertEqual(sp_handler.suppress_comment(), 'some comment')

    def test_multi_liner_all_2(self):
        """There is suppress comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           36,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(
            sp_handler.suppressed_checkers(), {'my.checker_1', 'my.checker_2'})
        self.assertEqual(
            sp_handler.suppress_comment(), 'some really long comment')

    def test_one_liner_some_checkers(self):
        """There is suppress comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           43,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(
            sp_handler.suppressed_checkers(), {'my.Checker_1', 'my.Checker_2'})
        self.assertEqual(
            sp_handler.suppress_comment(), 'some really really long comment')

    def test_multi_liner_some_checkers(self):
        """There is suppress comment above the bug line."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           50,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(sp_handler.suppressed_checkers(), set())
        self.assertIsNone(sp_handler.suppress_comment())

    def test_comment_characters(self):
        """Check for different special comment characters."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           57,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(
            sp_handler.suppressed_checkers(), {'my.checker_1', 'my.checker_2'})
        self.assertEqual(sp_handler.suppress_comment(), "i/';0 (*&^%$#@!)")

    def test_fancy_comment_characters(self):
        """Check fancy comment."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           64,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), {'my_checker_1'})
        self.assertEqual(
            sp_handler.suppress_comment(),
            "áúőóüöáé ▬▬▬▬▬▬▬▬▬▬ஜ۩۞۩ஜ▬▬▬▬▬▬▬▬▬▬")

    def test_no_fancy_comment(self):
        """Check no fancy comment."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_1,
                                           70,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), {'my_checker_1'})
        self.assertEqual(
            sp_handler.suppress_comment(),
            'WARNING! suppress comment is missing')

    def test_malformed_commment_format(self):
        """Check malformed comment."""
        sp_handler = SourceSuppressHandler(self.__tmp_srcfile_2,
                                           1,
                                           "0",
                                           "")
        res = sp_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(sp_handler.suppressed_checkers(), set())
        self.assertIsNone(sp_handler.suppress_comment())
