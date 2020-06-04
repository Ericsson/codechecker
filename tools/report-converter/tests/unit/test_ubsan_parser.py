# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform UndefinedBehaviorSanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.output_parser import Message
from codechecker_report_converter.sanitizers.ub.output_parser import \
    UBSANParser
from codechecker_report_converter.sanitizers.ub.analyzer_result import \
    UBSANAnalyzerResult

OLD_PWD = None


def setup_module():
    """ Setup the test tidy reprs for the test classes in the module. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'ubsan_output_test_files'))


def teardown_module():
    """ Restore environment after tests have ran. """
    global OLD_PWD
    os.chdir(OLD_PWD)


class UBSANPListConverterTestCase(unittest.TestCase):
    """ Test the output of the UBSANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = UBSANAnalyzerResult()
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

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        with open(expected_plist, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    def test_empty1(self):
        """ Test for empty Messages. """
        ret = self.analyzer_result.transform('empty1.out', self.cc_result_dir)
        self.assertFalse(ret)

    def test_empty2(self):
        """ Test for empty Messages with multiple line. """
        ret = self.analyzer_result.transform('empty2.out', self.cc_result_dir)
        self.assertFalse(ret)

    def test_ubsan1(self):
        """ Test for the ubsan1.plist file. """
        self.__check_analyzer_result('ubsan1.out', 'ubsan1.cpp_ubsan.plist',
                                     ['files/ubsan1.cpp'], 'ubsan1.plist')

    def test_ubsan2(self):
        """ Test for the ubsan2.plist file. """
        self.__check_analyzer_result('ubsan2.out', 'ubsan2.cpp_ubsan.plist',
                                     ['files/ubsan2.cpp'], 'ubsan2.plist')


class UBSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Undefined Behaviour
    Sanitizer output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = UBSANParser()
        self.ubsan1_repr = [
            Message(
                os.path.abspath('files/ubsan1.cpp'),
                4, 5,
                "signed integer overflow: 2147483647 + 1 cannot be "
                "represented in type 'int'",
                "UndefinedBehaviorSanitizer"),
        ]

        self.ubsan2_repr = [
            Message(
                os.path.abspath('files/ubsan2.cpp'),
                13, 10,
                "load of value 7, which is not a valid value for type "
                "'enum E'",
                "UndefinedBehaviorSanitizer"),
            Message(
                os.path.abspath('files/ubsan2.cpp'),
                21, 7,
                "load of value 2, which is not a valid value for type 'bool'",
                "UndefinedBehaviorSanitizer"),
        ]

    def test_empty1(self):
        """Test an empty output file."""
        messages = self.parser.parse_messages_from_file('empty1.out')
        self.assertEqual(messages, [])

    def test_empty2(self):
        """Test an output file that only contains empty lines."""
        messages = self.parser.parse_messages_from_file('empty2.out')
        self.assertEqual(messages, [])

    def test_absolute_path(self):
        """Test for absolute paths in Messages."""
        for tfile in ['abs.out', 'ubsan1.out']:
            messages = self.parser.parse_messages_from_file(tfile)
            self.assertNotEqual(len(messages), 0)
            for message in messages:
                self.assertTrue(os.path.isabs(message.path))

    def test_ubsan1(self):
        """ Test the generated Messages of ubsan1.out. """
        messages = self.parser.parse_messages_from_file('ubsan1.out')
        self.assertEqual(len(messages), len(self.ubsan1_repr))
        for message in messages:
            self.assertIn(message, self.ubsan1_repr)

    def test_ubsan2(self):
        """ Test the generated Messages of ubsan1.out. """
        messages = self.parser.parse_messages_from_file('ubsan2.out')
        self.assertEqual(len(messages), len(self.ubsan2_repr))
        for message in messages:
            self.assertIn(message, self.ubsan2_repr)
