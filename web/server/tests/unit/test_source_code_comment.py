# -*- coding: utf-8 -*-
#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Tests for source code comments in source file."""


import os
import unittest

from codechecker_common.source_code_comment_handler import \
    SourceCodeCommentHandler


class SourceCodeCommentTestCase(unittest.TestCase):
    """Tests for source code comments in source file."""

    @classmethod
    def setup_class(cls):
        """Initialize test source file references."""
        cls.__test_src_dir = os.path.join(
            os.path.dirname(__file__), 'source_code_comment_test_files')

        cls.__tmp_srcfile_1 = open(os.path.join(cls.__test_src_dir,
                                                'test_file_1'),
                                   encoding='utf-8', errors="ignore")
        cls.__tmp_srcfile_2 = open(os.path.join(cls.__test_src_dir,
                                                'test_file_2'),
                                   encoding='utf-8', errors="ignore")
        cls.__tmp_srcfile_3 = open(os.path.join(cls.__test_src_dir,
                                                'test_file_3'),
                                   encoding='utf-8', errors="ignore")

    @classmethod
    def teardown_class(cls):
        cls.__tmp_srcfile_1.close()
        cls.__tmp_srcfile_2.close()
        cls.__tmp_srcfile_3.close()

    def test_src_comment_first_line(self):
        """Bug is reported for the first line."""
        bug_line = 3
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertFalse(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_no_comment(self):
        """There is no comment above the bug line."""
        bug_line = 9
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertFalse(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_no_src_comment_comment(self):
        """There is no source comment above the bug line."""
        bug_line = 16
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [all] some comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multi_liner_all(self):
        """There is source code comment above the bug line."""
        bug_line = 23
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some long comment',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [all] some long\n '
                            '// comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_one_liner_all(self):
        """There is source code comment above the bug line."""
        bug_line = 29
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1', 'my_checker_2'},
                    'message': 'some comment',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [my_checker_1, '
                            'my_checker_2] some comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multi_liner_all_2(self):
        """There is source code comment above the bug line."""
        bug_line = 36
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my.checker_1', 'my.checker_2'},
                    'message': 'some really long comment',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [my.checker_1 '
                            'my.checker_2] some really\n // long comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_one_liner_some_checkers(self):
        """There is source code comment above the bug line."""
        bug_line = 43
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my.Checker_1', 'my.Checker_2'},
                    'message': 'some really really long comment',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [my.Checker_1, '
                            'my.Checker_2] some really\n // really\n'
                            ' // long comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multi_liner_some_checkers(self):
        """There is source code comment above the bug line."""
        bug_line = 50
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertFalse(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_comment_characters(self):
        """Check for different special comment characters."""
        bug_line = 57
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my.checker_1', 'my.checker_2'},
                    'message': "i/';0 (*&^%$#@!)",
                    'status': 'false_positive',
                    'line': "// codechecker_suppress [my.checker_1, "
                            "my.checker_2]\n // i/';0 (*&^%$#@!)\n"}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_fancy_comment_characters(self):
        """Check fancy comment."""
        bug_line = 64
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': "áúőóüöáé [▬▬▬▬▬▬▬▬▬▬ஜ۩۞۩ஜ▬▬▬▬▬▬▬▬▬▬]",
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [ my_checker_1 ]\n // '
                            'áúőóüöáé [▬▬▬▬▬▬▬▬▬▬ஜ۩۞۩ஜ▬▬▬▬▬▬▬▬▬▬]\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_no_fancy_comment(self):
        """Check no fancy comment."""
        bug_line = 70
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_1, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': 'WARNING! source code comment is missing',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [ my_checker_1 ]\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_malformed_commment_format(self):
        """Check malformed comment."""
        bug_line = 1
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_2,
                                                  bug_line)
        self.assertFalse(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_2, bug_line)
        self.assertEqual(len(source_line_comments), 0)

    def test_source_code_comment(self):
        """Check source code comment."""
        bug_line = 2
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'false_positive',
                    'line': '// codechecker_suppress [ all ] some comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_false_positive_comment(self):
        """Check False positive comment."""
        bug_line = 7
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'false_positive',
                    'line': '// codechecker_false_positive [ all ] '
                            'some comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_intentional_comment(self):
        """Check Intentional comment."""
        bug_line = 12
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'intentional',
                    'line': '// codechecker_intentional [ all ] '
                            'some comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_confirmed_comment(self):
        """Check Confirmed comment."""
        bug_line = 17
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'all'},
                    'message': 'some comment',
                    'status': 'confirmed',
                    'line': '// codechecker_confirmed [ all ] some comment\n'}
        self.assertDictEqual(expected, source_line_comments[0])

    def test_multiple_comments(self):
        """Check multiple comment."""
        bug_line = 23
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional',
                        'line': '// codechecker_intentional [ my.checker_1 ] '
                                'intentional comment\n'},
                    {
                        'checkers': {'my.checker_2'},
                        'message': 'confirmed bug',
                        'status': 'confirmed',
                        'line': '// codechecker_confirmed  [ my.checker_2 ] '
                                'confirmed bug\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_1')
        self.assertEqual(len(current_line_comments), 1)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[0]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[0]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_2')
        self.assertEqual(len(current_line_comments), 1)

        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.dummy')
        self.assertEqual(len(current_line_comments), 0)

    def test_multiple_multi_line_comments(self):
        """Check multi line long line comments."""
        bug_line = 31
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'long intentional bug comment',
                        'status': 'intentional',
                        'line': '// codechecker_intentional [ my.checker_1 ] '
                                'long intentional\n // bug comment\n'},
                    {
                        'checkers': {'my.checker_2'},
                        'message': 'long confirmed bug comment',
                        'status': 'confirmed',
                        'line': '// codechecker_confirmed  [ my.checker_2 ] '
                                'long confirmed\n // bug comment\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

    def test_multiple_all_comments(self):
        """Check multiple comment."""
        bug_line = 37
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = \
            sc_handler.get_source_line_comments(self.__tmp_srcfile_3, bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional',
                        'line': '// codechecker_intentional [ my.checker_1 ] '
                                'intentional comment\n'},
                    {
                        'checkers': {'all'},
                        'message': 'some comment',
                        'status': 'false_positive',
                        'line': '// codechecker_false_positive  [ all ] '
                                'some comment\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_1')
        self.assertEqual(len(current_line_comments), 2)

        self.assertEqual(current_line_comments[0]['message'],
                         expected[0]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[0]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   '')
        self.assertEqual(len(current_line_comments), 1)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.dummy')
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
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_3,
            bug_line)
        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional',
                        'line': '// codechecker_intentional [ my.checker_1 ] '
                                'intentional comment\n'
                    },
                    {
                        'checkers': {'my.checker_2', 'my.checker_1'},
                        'message': 'some comment',
                        'status': 'false_positive',
                        'line': '// codechecker_false_positive [ '
                                'my.checker_2, my.checker_1 ] some comment\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_1')
        self.assertEqual(len(current_line_comments), 2)

    def test_cstyle_comment(self):
        """
        C style comment in one line.
        /* codechecker_suppress [ my_checker_1 ] suppress comment */
        """

        bug_line = 76
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_1,
            bug_line)

        for line in source_line_comments:
            print(line)

        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': 'suppress comment',
                    'status': 'false_positive',
                    'line': '/* codechecker_suppress [ my_checker_1 ] '
                            'suppress comment */\n'}

        self.assertDictEqual(expected, source_line_comments[0])

    def test_cstyle_comment_multi_line(self):
        """
        Multi line C style comment.
        /* codechecker_suppress [ my_checker_1 ]
        some longer
        comment */
        """

        bug_line = 83
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_1,
            bug_line)

        for line in source_line_comments:
            print(line)

        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': 'some longer comment',
                    'status': 'false_positive',
                    'line': '/* codechecker_suppress [ my_checker_1 ]\n '
                            'some longer\n comment */\n'}

        self.assertDictEqual(expected, source_line_comments[0])

    def test_cstyle_comment_multi_nomsg(self):
        """
        Multi line C style comment.
        /* codechecker_suppress [ my_checker_1 ]
        */
        """

        bug_line = 89
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_1,
            bug_line)

        for line in source_line_comments:
            print(line)

        self.assertEqual(len(source_line_comments), 1)

        expected = [{
                        'checkers': {'my_checker_1'},
                        'message': 'WARNING! source code comment is missing',
                        'status': 'false_positive',
                        'line': '/* codechecker_suppress [ my_checker_1 ]'
                                '\n */\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])

    def test_cstyle_comment_multi_star(self):
        """
        Multi line C style comment.

        /* codechecker_suppress [ my_checker_1 ]
         * multi line
         * comment
         * again
         */
        """

        bug_line = 98
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_1,
            bug_line)

        for line in source_line_comments:
            print('-======')
            print(line)

        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': 'multi line comment again',
                    'status': 'false_positive',
                    'line': "/* codechecker_suppress [ my_checker_1 ]\n  * "
                            "multi line\n  * comment\n  * again\n  */\n"}

        self.assertDictEqual(expected, source_line_comments[0])

    def test_cstyle_comment_multi_line_mismatch(self):
        """
        Multi line C style comment start '/*' is in a different line
        from the codechecker review status comment.

        /*
          codechecker_suppress [ my_checker_1 ]
          multi line
          comment
          again
         */
        """

        bug_line = 108
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_1,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_1,
            bug_line)

        for line in source_line_comments:
            print('-======')
            print(line)

        self.assertEqual(len(source_line_comments), 1)

        expected = {'checkers': {'my_checker_1'},
                    'message': 'multi line comment again',
                    'status': 'false_positive',
                    'line': '  codechecker_suppress [ my_checker_1 ]\n   '
                            'multi line\n   comment\n   again\n  */\n'}

        self.assertDictEqual(expected, source_line_comments[0])

    def test_cstyle_multi_comment_multi_line(self):
        """
        Multi line C style comment with multiple review status comment.

        /* codechecker_false_positive [ my.checker_2, my.checker_1 ] comment
        codechecker_intentional [ my.checker_1 ] intentional comment */

        """

        bug_line = 49
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_3,
            bug_line)

        for line in source_line_comments:
            print(line)

        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment',
                        'status': 'intentional',
                        'line': 'codechecker_intentional [ my.checker_1 ] '
                                'intentional comment */\n'},
                    {
                        'checkers': {'my.checker_1', 'my.checker_2'},
                        'message': 'some comment',
                        'status': 'false_positive',
                        'line': '/* codechecker_false_positive [ '
                                'my.checker_2, my.checker_1 ] some comment\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_1')
        self.assertEqual(len(current_line_comments), 2)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[0]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[0]['status'])
        self.assertEqual(current_line_comments[1]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[1]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_2')
        self.assertEqual(len(current_line_comments), 1)

        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.dummy')
        self.assertEqual(len(current_line_comments), 0)

    def test_cstyle_multi_comment_multi_line_long(self):
        """
        Multi line C style comment with multiple review status comment.

        /* codechecker_false_positive [ my.checker_2, my.checker_1 ] comment
        which
        is
        long
        codechecker_intentional [ my.checker_1 ] intentional comment
        long
        again */

        """

        bug_line = 60
        sc_handler = SourceCodeCommentHandler()
        res = sc_handler.has_source_line_comments(self.__tmp_srcfile_3,
                                                  bug_line)
        self.assertTrue(res)

        source_line_comments = sc_handler.get_source_line_comments(
            self.__tmp_srcfile_3,
            bug_line)

        for line in source_line_comments:
            print(line)

        self.assertEqual(len(source_line_comments), 2)

        expected = [{
                        'checkers': {'my.checker_1'},
                        'message': 'intentional comment long again',
                        'status': 'intentional',
                        'line': 'codechecker_intentional [ my.checker_1 ] '
                                'intentional comment\n long\n again */\n'},
                    {
                        'checkers': {'my.checker_1', 'my.checker_2'},
                        'message': 'comment which is long',
                        'status': 'false_positive',
                        'line': '/* codechecker_false_positive [ '
                                'my.checker_2, my.checker_1 ] comment\n '
                                'which\n is\n long\n'
                    }]

        self.assertDictEqual(expected[0], source_line_comments[0])
        self.assertDictEqual(expected[1], source_line_comments[1])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_1')
        self.assertEqual(len(current_line_comments), 2)
        self.assertEqual(current_line_comments[0]['message'],
                         expected[0]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[0]['status'])
        self.assertEqual(current_line_comments[1]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[1]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.checker_2')
        self.assertEqual(len(current_line_comments), 1)

        self.assertEqual(current_line_comments[0]['message'],
                         expected[1]['message'])
        self.assertEqual(current_line_comments[0]['status'],
                         expected[1]['status'])

        current_line_comments = \
            sc_handler.filter_source_line_comments(self.__tmp_srcfile_3,
                                                   bug_line,
                                                   'my.dummy')
        self.assertEqual(len(current_line_comments), 0)
