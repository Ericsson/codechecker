# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform AddressSanitizer output to a plist file.
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
from codechecker_report_converter.sanitizers.address.output_parser import \
    ASANParser
from codechecker_report_converter.sanitizers.address.plist_converter import \
    ASANPlistConverter

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'asan_output_test_files'))

    asan_repr = [
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

    ASANOutputParserTestCase.asan_repr = asan_repr
    ASANPListConverterTestCase.asan_repr = asan_repr


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class ASANPListConverterTestCase(unittest.TestCase):
    """
    Test the output of the PListConverter, which converts Messages to plist
    format.
    """

    def setUp(self):
        """Setup the PListConverter."""
        self.plist_conv = ASANPlistConverter()

    def test_asan(self):
        """Test for the asan.plist file."""
        self.plist_conv.add_messages(self.asan_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/asan.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('asan.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()


class ASANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Address Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = ASANParser()

    def test_asan(self):
        """ Test the generated Messages of msan.out. """
        messages = self.parser.parse_messages_from_file('asan.out')
        self.assertEqual(len(messages), len(self.asan_repr))
        for message in messages:
            self.assertIn(message, self.asan_repr)
