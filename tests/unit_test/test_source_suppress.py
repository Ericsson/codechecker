#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
import os
import unittest
#import sys
import codecs
import tempfile

from codechecker_lib.suppress_handler import SourceSuppressHandler

test_file_content = u'''int test_func(int num){ // line 1
    cout << "test func" << endl;
    return 0;
}

// this is an ordinary comment
int test_func(int num){ // line 7
    cout << "test func" << endl;
    return 1;
}

// this is another non checker related comment
// codechecker_suppress [all] some comment
void test_func(int num){ // line 14
    // suppress all checker results
    cout << "test func" << endl;
}

// codechecker_suppress [all] some long
// comment
void test_func(int num){ // line 21
    // suppress all checker results
    cout << "test func" << endl;
}

// codechecker_suppress [my_checker_1, my_checker_2] some comment
void test_func(int num){ // line 27
    // suppress some checker results my_checker_2 and my_checker_2
    cout << "test func" << endl;
}

// codechecker_suppress [my.checker_1 my.checker_2] some really
// long comment
void test_func(int num){ // line 34
    cout << "test func" << endl;
}

// codechecker_suppress [my.Checker_1, my.Checker_2] some really
// really
// long comment
void test_func(int num){ // line 41
    cout << "test func" << endl;
}

// codechecker_suppress [my_checker_1, my_checker_2] some really
// really

void test_func(int num){ // line 48
    // wrong formatted suppress comment
    cout << "test func" << endl;
}

// codechecker_suppress [my.checker_1, my.checker_2]
// i/';0 (*&^%$#@!)
void test_func(int num){ // line 55
    // wrong formatted suppress comment
    cout << "test func"  << endl;
}

// codechecker_suppress [ my_checker_1 ]
// áúőóüöáé ▬▬▬▬▬▬▬▬▬▬ஜ۩۞۩ஜ▬▬▬▬▬▬▬▬▬▬
void test_func(int num){ // line 62
    // wrong formatted suppress comment
    cout << "test func"  << endl;
}

// codechecker_suppress [ my_checker_1 ]
void test_func(int num){ // line 68
    // wrong formatted suppress comment
    cout << "test func"  << endl;
}
'''

test_file_content_2 = '''// first line non checker comment
int test_func(int num){ // line 2
    cout << 'test func' << endl;
    return 0;
}
'''

class SourceSuppressTestCase(unittest.TestCase):

    __tmp_sourcefile = None

    def __make_tempfile(self, file_content):
        fd, temp_file_name = tempfile.mkstemp()
        os.close(fd)
        with codecs.open(temp_file_name, 'wt', 'UTF-8') as s_file:
            s_file.write(file_content)

        return temp_file_name

    def setUp(self):
        """ initialize test source file """
        self.__tmp_sourcefile = self.__make_tempfile(test_file_content)

    def tearDown(self):
        """ cleanup test source file """
        os.remove(self.__tmp_sourcefile)

    def test_suppress_first_line(self):
        """ bug is reported for the first line """
        test_handler = SourceSuppressHandler(self.__tmp_sourcefile, 1)
        res = test_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(test_handler.suppressed_checkers(), [])
        self.assertIsNone(test_handler.suppress_comment())

    def test_no_comment(self):
        """ there is no comment above the bug line"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 7)
        res = sp_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(sp_handler.suppressed_checkers(), [])
        self.assertIsNone(sp_handler.suppress_comment())

    def test_no_suppress_comment(self):
        """ there is suppress comment above the bug line"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 14)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['all'])
        self.assertEqual(sp_handler.suppress_comment(), 'some comment')

    def test_multi_liner_all(self):
        """ there is suppress comment above the bug line"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 21)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['all'])
        self.assertEqual(sp_handler.suppress_comment(), 'some long comment')

    def test_one_liner_all(self):
        """ there is suppress comment above the bug line"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 27)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['my_checker_1', 'my_checker_2'])
        self.assertEqual(sp_handler.suppress_comment(), 'some comment')

    def test_multi_liner_all(self):
        """ there is suppress comment above the bug line"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 34)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['my.checker_1', 'my.checker_2'])
        self.assertEqual(sp_handler.suppress_comment(), 'some really long comment')

    def test_one_liner_some_checkers(self):
        """doc"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 41)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['my.Checker_1', 'my.Checker_2'])
        self.assertEqual(sp_handler.suppress_comment(), 'some really really long comment')

    def test_multi_liner_some_checkers(self):
        """doc"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 48)
        res = sp_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(sp_handler.suppressed_checkers(), [])
        self.assertIsNone(sp_handler.suppress_comment())

    def test_comment_characters(self):
        """"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 55)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['my.checker_1', 'my.checker_2'])
        self.assertEqual(sp_handler.suppress_comment(), "i/';0 (*&^%$#@!)")

    def test_fancy_comment_characters(self):
        """ check fancy comment"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 62)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['my_checker_1'])
        self.assertEqual(sp_handler.suppress_comment(),
                         "áúőóüöáé ▬▬▬▬▬▬▬▬▬▬ஜ۩۞۩ஜ▬▬▬▬▬▬▬▬▬▬")

    def test_no_comment(self):
        """ check fancy comment"""
        sp_handler = SourceSuppressHandler(self.__tmp_sourcefile, 68)
        res = sp_handler.check_source_suppress()
        self.assertTrue(res)
        self.assertEqual(sp_handler.suppressed_checkers(), ['my_checker_1'])
        self.assertEqual(sp_handler.suppress_comment(), 'WARNING! suppress comment is missing')

    def test_malformed_commment_format(self):
        """"""
        test_sourcefile = self.__make_tempfile(test_file_content_2)

        sp_handler = SourceSuppressHandler(test_sourcefile, 1)
        res = sp_handler.check_source_suppress()
        self.assertFalse(res)
        self.assertEqual(sp_handler.suppressed_checkers(), [])
        self.assertIsNone(sp_handler.suppress_comment())

        os.remove(test_sourcefile)



