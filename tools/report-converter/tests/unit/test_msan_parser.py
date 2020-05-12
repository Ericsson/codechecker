# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform MemorySanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.output_parser import Event, Message
from codechecker_report_converter.sanitizers.memory.output_parser import \
    MSANParser
from codechecker_report_converter.sanitizers.memory.analyzer_result import \
    MSANAnalyzerResult

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'msan_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class MSANPListConverterTestCase(unittest.TestCase):
    """ Test the output of the MSANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = MSANAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_msan(self):
        """ Test for the msan.plist file. """
        self.analyzer_result.transform('msan.out', self.cc_result_dir)

        with open('msan.plist', mode='rb') as pfile:
            exp = plistlib.load(pfile)

        plist_file = os.path.join(self.cc_result_dir, 'msan.cpp_msan.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/msan.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)


class MSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Memory Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """ Setup the OutputParser. """
        self.parser = MSANParser()
        self.msan_repr = [
            Message(
                os.path.abspath('files/msan.cpp'),
                7, 7,
                "use-of-uninitialized-value",
                "MemorySanitizer",
                [Event(
                    os.path.abspath('files/msan.cpp'),
                    7, 7,
                    "    #0 0x4940da in main files/msan.cpp:7:7"
                )],
                [Event(
                    os.path.abspath('files/msan.cpp'),
                    7, 7,
                    "    #0 0x4940da in main files/msan.cpp:7:7\n"
                    "    #1 0x7fed9df58b96 in __libc_start_main (??)\n"
                    "    #2 0x41b2d9 in _start (??)\n"
                )]),
        ]

    def test_msan(self):
        """ Test the generated Messages of msan.out. """
        messages = self.parser.parse_messages_from_file('msan.out')
        self.assertEqual(len(messages), len(self.msan_repr))
        for message in messages:
            self.assertIn(message, self.msan_repr)
