# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Tests for source code comments in source file."""

import os
import unittest

from libcodechecker.source_code_comment_handler import SourceCodeCommentHandler


class SourceCodeCommentTestCase(unittest.TestCase):
    """Tests for source code comments in source file."""

    @classmethod
    def setup_class(cls):
        """Initialize test source file references."""
        cls.__test_src_dir = os.path.join(
            os.path.dirname(__file__), 'source_code_comment_test_files')

        cls.__tmp_srcfile_1 = os.path.join(cls.__test_src_dir, 'test_file_1')
        cls.__tmp_srcfile_2 = os.path.join(cls.__test_src_dir, 'test_file_2')
        cls.__tmp_srcfile_3 = os.path.join(cls.__test_src_dir, 'test_file_3')

    def test_src_comment_first_line(self):
        """Bug is reported for the first line."""
        bug_line = 3
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertFalse(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_no_comment(self):
        """There is no comment above the bug line."""
        bug_line = 9
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertFalse(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_no_src_comment_comment(self):
        """There is no source comment above the bug line."""
        bug_line = 16
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multi_liner_all(self):
        """There is source code comment above the bug line."""
        bug_line = 23
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some long comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_one_liner_all(self):
        """There is source code comment above the bug line."""
        bug_line = 29
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1', 'my_checker_2'},
                    'message': 'some comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multi_liner_all_2(self):
        """There is source code comment above the bug line."""
        bug_line = 36
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my.checker_1', 'my.checker_2'},
                    'message': 'some really long comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_one_liner_some_checkers(self):
        """There is source code comment above the bug line."""
        bug_line = 43
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my.Checker_1', 'my.Checker_2'},
                    'message': 'some really really long comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multi_liner_some_checkers(self):
        """There is source code comment above the bug line."""
        bug_line = 50
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertFalse(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_comment_characters(self):
        """Check for different special comment characters."""
        bug_line = 57
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my.checker_1', 'my.checker_2'},
                    'message': "i/';0 (*&^%$#@!)",
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_fancy_comment_characters(self):
        """Check fancy comment."""
        bug_line = 64
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': "áúőóüöáé ▬▬▬▬▬▬▬▬▬▬ஜ۩۞۩ஜ▬▬▬▬▬▬▬▬▬▬",
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_no_fancy_comment(self):
        """Check no fancy comment."""
        bug_line = 70
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_1)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': 'WARNING! source code comment is missing',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_malformed_commment_format(self):
        """Check malformed comment."""
        bug_line = 1
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_2)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertFalse(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_source_code_comment(self):
        """Check source code comment."""
        bug_line = 2
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_false_positive_comment(self):
        """Check False positive comment."""
        bug_line = 7
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'false_positive'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_intentional_comment(self):
        """Check Intentional comment."""
        bug_line = 12
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'intentional'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_confirmed_comment(self):
        """Check Confirmed comment."""
        bug_line = 17
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'confirmed'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multiple_comments(self):
        """Check multiple comment."""
        bug_line = 23
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional'},
                    {
                        'checkers': {'my.checker_2'},
                        'message': 'confirmed bug',
                        'status': 'confirmed'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line, 'my.checker_1')
        self.assertEqual(len(current_line_comments), 1)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[0]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[0]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line, 'my.checker_2')
        self.assertEqual(len(current_line_comments), 1)

        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line, 'my.dummy')
        self.assertEqual(len(current_line_comments), 0)

    def test_multiple_multi_line_comments(self):
        """Check multi line long line comments."""
        bug_line = 31
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'long intentional bug comment',
                        'status': 'intentional'},
                    {
                        'checkers': {'my.checker_2'},
                        'message': 'long confirmed bug comment',
                        'status': 'confirmed'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

    def test_multiple_all_comments(self):
        """Check multiple comment."""
        bug_line = 37
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional'},
                    {
                        'checkers': {'all'},
                        'message': 'some comment',
                        'status': 'false_positive'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line, 'my.checker_1')
        self.assertEqual(len(current_line_comments), 1)

        self.assertEqual(current_line_comments[0]['message'],
                         expected[0]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[0]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line, '')
        self.assertEqual(len(current_line_comments), 1)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line, 'my.dummy')
        self.assertEqual(len(current_line_comments), 1)

        self.assertEqual(len(current_line_comments), 1)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

    def test_multiple_checker_name_comments(self):
        """
        Check multiple comment where same checker name are given for multiple
        source code comment.
        """

        bug_line = 43
        sc_handler = SourceCodeCommentHandler(self.__tmp_srcfile_3)
        res = sc_handler.has_source_line_comments(bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional'
                    },
                    {
                        'checkers': {'my.checker_2', 'my.checker_1'},
                        'message': 'some comment',
                        'status': 'false_positive'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(bug_line,
                                                   'my.checker_1')
        self.assertEqual(len(current_line_comments), 2)
