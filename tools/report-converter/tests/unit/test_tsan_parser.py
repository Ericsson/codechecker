# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform ThreadSanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.output_parser import Event, Message
from codechecker_report_converter.sanitizers.thread.output_parser import \
    TSANParser
from codechecker_report_converter.sanitizers.thread.analyzer_result import \
    TSANAnalyzerResult

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'tsan_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class TSANAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the TSANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = TSANAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_tsan(self):
        """ Test for the tsan.plist file. """
        self.analyzer_result.transform('tsan.out', self.cc_result_dir)

        with open('tsan.plist', mode='rb') as pfile:
            exp = plistlib.load(pfile)

        plist_file = os.path.join(self.cc_result_dir, 'tsan.cpp_tsan.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/tsan.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)


class TSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Thread Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = TSANParser()
        self.tsan_repr = [
            Message(
                os.path.abspath('files/tsan.cpp'),
                24, 2,
                "SEGV on unknown address 0x000000000000 (pc 0x0000004b525c bp "
                "0x7fff93b54920 sp 0x7fff93b548b0 T23755)",
                "ThreadSanitizer",
                [Event(
                    os.path.abspath('files/tsan.cpp'),
                    24, 2,
                    "    #1 main files/tsan.cpp:24:2 (a.out+0x4b529e)"),
                 Event(
                    os.path.abspath('files/tsan.cpp'),
                    18, 14,
                    "    #0 insert_in_table(unsigned long, int) "
                    "files/tsan.cpp:18:14 (a.out+0x4b525b)"
                 )],
                [Event(
                    os.path.abspath('files/tsan.cpp'),
                    24, 2,
                    "==23755==The signal is caused by a WRITE memory access.\n"
                    "==23755==Hint: address points to the zero page.\n"
                    "    #0 insert_in_table(unsigned long, int) "
                    "files/tsan.cpp:18:14 (a.out+0x4b525b)\n"
                    "    #1 main files/tsan.cpp:24:2 (a.out+0x4b529e)\n"
                    "    #2 __libc_start_main /build/glibc-OTsEL5/glibc-2.27/"
                    "csu/../csu/libc-start.c:310 (libc.so.6+0x21b96)\n"
                    "    #3 _start <null> (a.out+0x41c8d9)\n"
                )]),
        ]

    def test_tsan(self):
        """ Test the generated Messages of tsan.out. """
        messages = self.parser.parse_messages_from_file('tsan.out')
        self.assertEqual(len(messages), len(self.tsan_repr))
        for message in messages:
            self.assertIn(message, self.tsan_repr)
