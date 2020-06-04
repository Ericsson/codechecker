# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform a Clang Tidy output file to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.output_parser import Message, Event
from codechecker_report_converter.clang_tidy.output_parser import \
    ClangTidyParser
from codechecker_report_converter.clang_tidy.analyzer_result import \
    ClangTidyAnalyzerResult

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), 'tidy_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class ClangTidyOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts a Clang Tidy output
    file to zero or more tidy_output_converter.Message.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = ClangTidyParser()

        # tidy1.out Message/Note representation
        self.tidy1_repr = [
            Message(
                os.path.abspath('files/test.cpp'),
                8, 12,
                'Division by zero',
                'clang-analyzer-core.DivideZero',
                [Event(
                    os.path.abspath('files/test.cpp'),
                    8, 12,
                    'Division by zero')]),
            Message(
                os.path.abspath('files/test.cpp'),
                8, 12,
                'remainder by zero is undefined',
                'clang-diagnostic-division-by-zero')
        ]

        # tidy2.out Message/Note representation
        self.tidy2_repr = [
            Message(
                os.path.abspath('files/test2.cpp'),
                5, 7,
                "unused variable 'y'",
                'clang-diagnostic-unused-variable'),
            Message(
                os.path.abspath('files/test2.cpp'),
                13, 12,
                'Division by zero',
                'clang-analyzer-core.DivideZero',
                [
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        9, 7,
                        "Left side of '||' is false"),
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        9, 3,
                        'Taking false branch'),
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        13, 12,
                        'Division by zero')
                ]),
            Message(
                os.path.abspath('files/test2.cpp'),
                13, 12,
                'remainder by zero is undefined',
                'clang-diagnostic-division-by-zero'),
        ]

        # tidy2_v6.out Message/Note representation
        self.tidy2_v6_repr = [
            Message(
                os.path.abspath('files/test2.cpp'),
                13, 12,
                'Division by zero',
                'clang-analyzer-core.DivideZero',
                [
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        9, 7,
                        "Left side of '||' is false"),
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        9, 16,
                        "Assuming 'x' is 0"),
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        9, 3,
                        'Taking false branch'),
                    Event(
                        os.path.abspath('files/test2.cpp'),
                        13, 12,
                        'Division by zero')
                ]),
            Message(
                os.path.abspath('files/test2.cpp'),
                13, 12,
                'remainder by zero is undefined',
                'clang-diagnostic-division-by-zero'),
        ]

        # tidy3.out Message/Note representation
        self.tidy3_repr = [
            Message(
                os.path.abspath('files/test3.cpp'),
                4, 12,
                'use nullptr',
                'modernize-use-nullptr',
                None,
                None,
                [Event(
                    os.path.abspath('files/test3.cpp'),
                    4, 12,
                    'nullptr')]),
            Message(
                os.path.abspath('files/test3.hh'),
                6, 6,
                "Dereference of null pointer (loaded from variable 'x')",
                'clang-analyzer-core.NullDereference',
                [
                    Event(
                        os.path.abspath('files/test3.cpp'),
                        4, 3,
                        "'x' initialized to a null pointer value"),
                    Event(
                        os.path.abspath('files/test3.cpp'),
                        6, 11,
                        "Assuming 'argc' is > 3"),
                    Event(
                        os.path.abspath('files/test3.cpp'),
                        6, 3,
                        'Taking true branch'),
                    Event(
                        os.path.abspath('files/test3.cpp'),
                        7, 9,
                        "Passing null pointer value via 1st parameter 'x'"),
                    Event(
                        os.path.abspath('files/test3.cpp'),
                        7, 5,
                        "Calling 'bar'"),
                    Event(
                        os.path.abspath('files/test3.hh'),
                        6, 6,
                        "Dereference of null pointer (loaded from variable "
                        "'x')")
                ])
        ]

        # tidy5.out Message/Note representation
        self.tidy5_repr = [
            Message(
                os.path.abspath('files/test4.cpp'),
                3, 26,
                'identifier after literal will be treated '
                'as a reserved user-defined literal suffix in C++11',
                'clang-diagnostic-c++11-compat-reserved-user-defined-literal'),
            Message(
                os.path.abspath('files/test4.cpp'),
                10, 12,
                'Division by zero',
                'clang-analyzer-core.DivideZero',
                [Event(
                    os.path.abspath('files/test4.cpp'),
                    10, 12,
                    'Division by zero')]),
            Message(
                os.path.abspath('files/test4.cpp'),
                10, 12,
                'remainder by zero is undefined',
                'clang-diagnostic-division-by-zero')
        ]

        # tidy5_v6.out Message/Note representation
        self.tidy5_v6_repr = [
            Message(
                os.path.abspath('files/test4.cpp'),
                3, 26,
                'invalid suffix on literal; C++11 requires a space '
                'between literal and identifier',
                'clang-diagnostic-reserved-user-defined-literal'),
            Message(
                os.path.abspath('files/test4.cpp'),
                10, 12,
                'remainder by zero is undefined',
                'clang-diagnostic-division-by-zero')
        ]

        # tidy6.out Message/Note representation
        self.tidy6_repr = [
            Message(
                os.path.abspath('files/test5.cpp'),
                10, 9,
                'no matching function for call to \'get_type\'',
                'clang-diagnostic-error',
                [
                    Event(
                        os.path.abspath('files/test5.cpp'),
                        2, 18,
                        'candidate template ignored: substitution failure '
                        '[with T = int *]: type \'int *\' cannot be used '
                        'prior to \'::\' because it has no members'),
                    Event(
                        os.path.abspath('files/test5.cpp'),
                        5, 6,
                        'candidate template ignored: substitution failure '
                        '[with T = int]: array size is negative'),
                ]
            )]

    def test_absolute_path(self):
        """Test for absolute paths in Messages."""
        for tfile in ['abs.out', 'tidy1.out']:
            messages = self.parser.parse_messages_from_file(tfile)
            self.assertNotEqual(len(messages), 0)
            for message in messages:
                self.assertTrue(os.path.isabs(message.path))

    def test_empty1(self):
        """Test an empty ClangTidy output file."""
        messages = self.parser.parse_messages_from_file('empty1.out')
        self.assertEqual(messages, [])

    def test_empty2(self):
        """Test a ClangTidy output file that only contains empty lines."""
        messages = self.parser.parse_messages_from_file('empty2.out')
        self.assertEqual(messages, [])

    def test_tidy1(self):
        """Test the generated Messages of tidy1.out ClangTidy output file."""
        messages = self.parser.parse_messages_from_file('tidy1.out')
        self.assertEqual(len(messages), len(self.tidy1_repr))
        for message in messages:
            self.assertIn(message, self.tidy1_repr)

    def test_tidy1_v6(self):
        """Test the generated Messages of tidy1.out ClangTidy v6 output
        file."""
        messages = self.parser.parse_messages_from_file('tidy1_v6.out')
        self.assertEqual(len(messages), len(self.tidy1_repr))
        for message in messages:
            self.assertIn(message, self.tidy1_repr)

    def test_tidy2(self):
        """Test the generated Messages of tidy2.out ClangTidy output file."""
        messages = self.parser.parse_messages_from_file('tidy2.out')
        self.assertEqual(len(messages), len(self.tidy2_repr))
        for message in messages:
            self.assertIn(message, self.tidy2_repr)

    def test_tidy2_v6(self):
        """Test the generated Messages of tidy2.out ClangTidy v6 output
        file."""
        messages = self.parser.parse_messages_from_file('tidy2_v6.out')
        self.assertEqual(len(messages), len(self.tidy2_v6_repr))
        for message in messages:
            self.assertIn(message, self.tidy2_v6_repr)

    def test_tidy3(self):
        """Test the generated Messages of tidy3.out ClangTidy output file."""
        messages = self.parser.parse_messages_from_file('tidy3.out')
        self.assertEqual(len(messages), len(self.tidy3_repr))
        for message in messages:
            self.assertIn(message, self.tidy3_repr)

    def test_tidy4(self):
        """
        Test the generated Messages of tidy4.out ClangTidy output file.
        This is an uncomplete file which is equal with tidy1.out except it's
        missing the last two lines.
        """
        messages = self.parser.parse_messages_from_file('tidy4.out')
        self.assertEqual(len(messages), len(self.tidy1_repr))
        for message in messages:
            self.assertIn(message, self.tidy1_repr)

    def test_tidy5(self):
        """
        Test the grenerated Messages of tidy5.out ClangTidy output file.
        This is an uncomplete file which is equal with tidy1.out except it's
        missing the last two lines.
        """
        messages = self.parser.parse_messages_from_file('tidy5.out')
        for message in messages:
            self.assertIn(message, self.tidy5_repr)

    def test_tidy5_v6(self):
        """
        Test the grenerated Messages of tidy5_v6.out ClangTidy output file.
        This is an uncomplete file which is equal with tidy1.out except it's
        missing the last two lines.
        """
        messages = self.parser.parse_messages_from_file('tidy5_v6.out')
        for message in messages:
            self.assertIn(message, self.tidy5_v6_repr)

    def test_tidy6(self):
        """
        Test the generated Messages of tidy6.out ClangTidy output file.
        """
        messages = self.parser.parse_messages_from_file('tidy6.out')
        for message in messages:
            self.assertIn(message, self.tidy6_repr)


class ClangTidyAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the ClangTidyAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = ClangTidyAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def __check_analyzer_result(self, analyzer_result, analyzer_result_plist,
                                source_files, expected_plist):
        """ Check the result of the analyzer transformation. """

        self.analyzer_result.transform(analyzer_result, self.cc_result_dir)

        plist_file = os.path.join(self.cc_result_dir, analyzer_result_plist)
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'] = source_files

        with open(expected_plist, mode='rb') as pfile:
            exp = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)

    def test_empty1(self):
        """ Test for empty Messages. """
        ret = self.analyzer_result.transform('empty1.out', self.cc_result_dir)
        self.assertFalse(ret)

    def test_empty2(self):
        """ Test for empty Messages with multiple line. """
        ret = self.analyzer_result.transform('empty2.out', self.cc_result_dir)
        self.assertFalse(ret)

    def test_tidy1(self):
        """ Test for the tidy1.plist file. """
        self.__check_analyzer_result('tidy1.out', 'test.cpp_clang-tidy.plist',
                                     ['files/test.cpp'], 'tidy1.plist')

    def test_tidy2(self):
        """ Test for the tidy2.plist file. """
        self.__check_analyzer_result('tidy2.out', 'test2.cpp_clang-tidy.plist',
                                     ['files/test2.cpp'], 'tidy2.plist')

    def test_tidy3(self):
        """ Test for the tidy3.plist file. """
        self.__check_analyzer_result('tidy3.out', 'test3.cpp_clang-tidy.plist',
                                     ['files/test3.cpp'],
                                     'tidy3_cpp.plist')

        self.__check_analyzer_result('tidy3.out', 'test3.hh_clang-tidy.plist',
                                     ['files/test3.hh', 'files/test3.cpp'],
                                     'tidy3_hh.plist')
