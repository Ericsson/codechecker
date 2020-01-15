# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform MemorySanitizer output to a plist file.
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

from report_converter.converter.output_parser import Event, Message
from report_converter.converter.sanitizers.memory.output_parser import \
    MSANOutputParser
from report_converter.converter.sanitizers.memory.plist_converter import \
    MSANPlistConverter

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'msan_output_test_files'))

    msan_repr = [
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

    MSANOutputParserTestCase.msan_repr = msan_repr
    MSANPListConverterTestCase.msan_repr = msan_repr


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class MSANPListConverterTestCase(unittest.TestCase):
    """
    Test the output of the PListConverter, which converts Messages to plist
    format.
    """

    def setUp(self):
        """Setup the PListConverter."""
        self.plist_conv = MSANPlistConverter()

    def test_msan(self):
        """Test for the msan.plist file."""
        self.plist_conv.add_messages(self.msan_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/msan.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('msan.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()


class MSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Memory Sanitizer
    output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = MSANOutputParser()

    def test_msan(self):
        """ Test the generated Messages of msan.out. """
        messages = self.parser.parse_messages_from_file('msan.out')
        self.assertEqual(len(messages), len(self.msan_repr))
        for message in messages:
            self.assertIn(message, self.msan_repr)
