# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform AddressSanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.output_parser import Event, Message
from codechecker_report_converter.sanitizers.address.output_parser import \
    ASANParser
from codechecker_report_converter.sanitizers.address.analyzer_result import \
    ASANAnalyzerResult

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), 'asan_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class ASANAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the ASANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = ASANAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_asan(self):
        """ Test for the asan.plist file. """
        self.analyzer_result.transform('asan.out', self.cc_result_dir)

        with open('asan.plist', mode='rb') as pfile:
            exp = plistlib.load(pfile)

        plist_file = os.path.join(self.cc_result_dir, 'asan.cpp_asan.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/asan.cpp'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)


class ASANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Address Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = ASANParser()
        self.asan_repr = [
            Message(
                os.path.abspath('files/asan.cpp'),
                5, 10,
                "heap-use-after-free on address 0x614000000044 at pc "
                "0x0000004f4b45 bp 0x7ffd40559120 sp 0x7ffd40559118",
                "AddressSanitizer",
                [Event(
                    os.path.abspath('files/asan.cpp'),
                    5, 10,
                    "    #0 0x4f4b44 in main files/asan.cpp:5:10"
                )],
                [Event(
                    os.path.abspath('files/asan.cpp'),
                    5, 10,
                    "READ of size 4 at 0x614000000044 thread T0\n"
                    "    #0 0x4f4b44 in main files/asan.cpp:5:10\n"
                    "    #1 0x7f334b52eb96 in __libc_start_main (??)\n"
                    "    #2 0x41aaf9 in _start (??)\n"
                )]
            ),
        ]

    def test_asan(self):
        """ Test the generated Messages of msan.out. """
        messages = self.parser.parse_messages_from_file('asan.out')
        self.assertEqual(len(messages), len(self.asan_repr))

        for message in messages:
            self.assertIn(message, self.asan_repr)
