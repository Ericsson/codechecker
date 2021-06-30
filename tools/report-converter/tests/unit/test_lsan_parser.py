# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform LeakSanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.output_parser import Event, Message
from codechecker_report_converter.sanitizers.leak.output_parser import \
    LSANParser
from codechecker_report_converter.sanitizers.leak.analyzer_result import \
    LSANAnalyzerResult

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'lsan_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class LSANPListConverterTestCase(unittest.TestCase):
    """ Test the output of the LSANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = LSANAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_san(self):
        """ Test for the lsan.plist file. """
        self.analyzer_result.transform('lsan.out', self.cc_result_dir)

        with open('lsan.plist', mode='rb') as pfile:
            exp = plistlib.load(pfile)

        plist_file = os.path.join(self.cc_result_dir, 'lsan.c_lsan.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/lsan.c'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)


class LSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Leak Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """ Setup the OutputParser. """
        self.parser = LSANParser()
        self.lsan_repr = [
            Message(
                os.path.abspath('files/lsan.c'),
                4, 7,
                "detected memory leaks",
                "LeakSanitizer",
                [Event(
                    os.path.abspath('files/lsan.c'),
                    4, 7,
                    "    #1 0x4da26a in main files/lsan.c:4:7"
                )],
                [Event(
                    os.path.abspath('files/lsan.c'),
                    4, 7,
                    "Direct leak of 7 byte(s) in 1 object(s) allocated from:\n"
                    "    #0 0x4af01b in __interceptor_malloc /projects/"
                    "compiler-rt/lib/asan/asan_malloc_linux.cc:52:3\n"
                    "    #1 0x4da26a in main files/lsan.c:4:7\n"
                    "    #2 0x7f076fd9cec4 in __libc_start_main "
                    "libc-start.c:287\n"
                    "SUMMARY: AddressSanitizer: 7 byte(s) "
                    "leaked in 1 allocation(s)\n"
                )]),
        ]

    def test_lsan(self):
        """ Test the generated Messages of lsan.out. """
        messages = self.parser.parse_messages_from_file('lsan.out')
        self.assertEqual(len(messages), len(self.lsan_repr))
        for message in messages:
            self.assertIn(message, self.lsan_repr)
