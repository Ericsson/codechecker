# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform UndefinedBehaviorSanitizer output to a plist file.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import copy
import os
import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

from warning_to_plist.converter.output_parser import Message
from warning_to_plist.converter.sanitizers.ub.output_parser import \
    UBSANOutputParser
from warning_to_plist.converter.sanitizers.ub.plist_converter import \
    UBSANPlistConverter

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'ubsan_output_test_files'))

    ubsan1_repr = [
        Message(
            os.path.abspath('files/ubsan1.cpp'),
            4, 5,
            "signed integer overflow: 2147483647 + 1 cannot be represented "
            "in type 'int'",
            "UndefinedBehaviorSanitizer"),
    ]

    ubsan2_repr = [
        Message(
            os.path.abspath('files/ubsan2.cpp'),
            13, 10,
            "load of value 7, which is not a valid value for type 'enum E'",
            "UndefinedBehaviorSanitizer"),
        Message(
            os.path.abspath('files/ubsan2.cpp'),
            21, 7,
            "load of value 2, which is not a valid value for type 'bool'",
            "UndefinedBehaviorSanitizer"),
    ]

    UBSANOutputParserTestCase.ubsan1_repr = ubsan1_repr
    UBSANOutputParserTestCase.ubsan2_repr = ubsan2_repr
    UBSANPListConverterTestCase.ubsan1_repr = ubsan1_repr
    UBSANPListConverterTestCase.ubsan2_repr = ubsan2_repr


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class UBSANPListConverterTestCase(unittest.TestCase):
    """
    Test the output of the PListConverter, which converts Messages to plist
    format.
    """

    def setUp(self):
        """Setup the PListConverter."""
        self.plist_conv = UBSANPlistConverter()

    def test_empty(self):
        """Test for empty Messages."""
        orig_plist = copy.deepcopy(self.plist_conv.plist)

        self.plist_conv.add_messages([])
        self.assertDictEqual(orig_plist, self.plist_conv.plist)

        output = StringIO()
        self.plist_conv.write(output)

        with open('empty.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()

    def test_ubsan1(self):
        """Test for the ubsan1.plist file."""
        self.plist_conv.add_messages(self.ubsan1_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/ubsan1.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('ubsan1.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()

    def test_ubsan2(self):
        """Test for the ubsan2.plist file."""
        self.plist_conv.add_messages(self.ubsan2_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/ubsan2.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('ubsan2.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()


class UBSANOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts an Undefined Behaviour
    Sanitizer output file to zero or more Message object.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = UBSANOutputParser()

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
