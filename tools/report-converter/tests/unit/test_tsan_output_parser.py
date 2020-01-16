# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform ThreadSanitizer output to a plist file.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

from codechecker_report_converter.output_parser import Event, Message
from codechecker_report_converter.sanitizers.thread.output_parser import \
    TSANParser
from codechecker_report_converter.sanitizers.thread.plist_converter import \
    TSANPlistConverter

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'tsan_output_test_files'))

    tsan_repr = [
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

    TSANOutputParserTestCase.tsan_repr = tsan_repr
    TSANPListConverterTestCase.tsan_repr = tsan_repr


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class TSANPListConverterTestCase(unittest.TestCase):
    """
    Test the output of the PListConverter, which converts Messages to plist
    format.
    """

    def setUp(self):
        """Setup the PListConverter."""
        self.plist_conv = TSANPlistConverter()

    def test_tsan(self):
        """Test for the tsan.plist file."""
        self.plist_conv.add_messages(self.tsan_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/tsan.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('tsan.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()


class TSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Thread Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = TSANParser()

    def test_tsan(self):
        """ Test the generated Messages of tsan.out. """
        messages = self.parser.parse_messages_from_file('tsan.out')
        self.assertEqual(len(messages), len(self.tsan_repr))
        for message in messages:
            self.assertIn(message, self.tsan_repr)
