# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform a Clang Tidy output file to a plist file.
"""

import copy
import os
import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO

import libcodechecker.analyze.tidy_output_converter as tidy_out_conv

OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), 'tidy_output_test_files'))

    # tidy1.out Message/Note representation
    tidy1_repr = [
        tidy_out_conv.Message(
            os.path.abspath('files/test.cpp'),
            8, 12,
            'Division by zero',
            'clang-analyzer-core.DivideZero',
            None,
            [tidy_out_conv.Note(
                os.path.abspath('files/test.cpp'),
                8, 12,
                'Division by zero')]),
        tidy_out_conv.Message(
            os.path.abspath('files/test.cpp'),
            8, 12,
            'remainder by zero is undefined',
            'clang-diagnostic-division-by-zero')
    ]

    # tidy2.out Message/Note representation
    tidy2_repr = [
        tidy_out_conv.Message(
            os.path.abspath('files/test2.cpp'),
            5, 7,
            "unused variable 'y'",
            'clang-diagnostic-unused-variable'),
        tidy_out_conv.Message(
            os.path.abspath('files/test2.cpp'),
            13, 12,
            'Division by zero',
            'clang-analyzer-core.DivideZero',
            None,
            [
                tidy_out_conv.Note(
                    os.path.abspath('files/test2.cpp'),
                    9, 7,
                    "Left side of '||' is false"),
                tidy_out_conv.Note(
                    os.path.abspath('files/test2.cpp'),
                    9, 3,
                    'Taking false branch'),
                tidy_out_conv.Note(
                    os.path.abspath('files/test2.cpp'),
                    13, 12,
                    'Division by zero')
            ]),
        tidy_out_conv.Message(
            os.path.abspath('files/test2.cpp'),
            13, 12,
            'remainder by zero is undefined',
            'clang-diagnostic-division-by-zero'),
    ]

    # tidy3.out Message/Note representation
    tidy3_repr = [
        tidy_out_conv.Message(
            os.path.abspath('files/test3.cpp'),
            4, 12,
            'use nullptr',
            'modernize-use-nullptr',
            [tidy_out_conv.Note(
                os.path.abspath('files/test3.cpp'),
                4, 12,
                'nullptr')]),
        tidy_out_conv.Message(
            os.path.abspath('files/test3.hh'),
            6, 6,
            "Dereference of null pointer (loaded from variable 'x')",
            'clang-analyzer-core.NullDereference',
            None,
            [
                tidy_out_conv.Note(
                    os.path.abspath('files/test3.cpp'),
                    4, 3,
                    "'x' initialized to a null pointer value"),
                tidy_out_conv.Note(
                    os.path.abspath('files/test3.cpp'),
                    6, 11,
                    "Assuming 'argc' is > 3"),
                tidy_out_conv.Note(
                    os.path.abspath('files/test3.cpp'),
                    6, 3,
                    'Taking true branch'),
                tidy_out_conv.Note(
                    os.path.abspath('files/test3.cpp'),
                    7, 9,
                    "Passing null pointer value via 1st parameter 'x'"),
                tidy_out_conv.Note(
                    os.path.abspath('files/test3.cpp'),
                    7, 5,
                    "Calling 'bar'"),
                tidy_out_conv.Note(
                    os.path.abspath('files/test3.hh'),
                    6, 6,
                    "Dereference of null pointer (loaded from variable 'x')")
            ])
    ]

    TidyOutputParserTestCase.tidy1_repr = tidy1_repr
    TidyOutputParserTestCase.tidy2_repr = tidy2_repr
    TidyOutputParserTestCase.tidy3_repr = tidy3_repr
    TidyPListConverterTestCase.tidy1_repr = tidy1_repr
    TidyPListConverterTestCase.tidy2_repr = tidy2_repr
    TidyPListConverterTestCase.tidy3_repr = tidy3_repr


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class TidyOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts a Clang Tidy output
    file to zero or more tidy_output_converter.Message.
    """

    def setUp(self):
        """Setup the OutputParser."""
        self.parser = tidy_out_conv.OutputParser()

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

    def test_tidy2(self):
        """Test the generated Messages of tidy2.out ClangTidy output file."""
        messages = self.parser.parse_messages_from_file('tidy2.out')
        self.assertEqual(len(messages), len(self.tidy2_repr))
        for message in messages:
            self.assertIn(message, self.tidy2_repr)

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


class TidyPListConverterTestCase(unittest.TestCase):
    """
    Test the output of the PListConverter, which converts Messages to plist
    format.
    """

    def setUp(self):
        """Setup the PListConverter."""
        self.plist_conv = tidy_out_conv.PListConverter()

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

    def test_tidy1(self):
        """Test for the tidy1.plist file."""
        self.plist_conv.add_messages(self.tidy1_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/test.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('tidy1.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()

    def test_tidy2(self):
        """Test for the tidy2.plist file."""
        self.plist_conv.add_messages(self.tidy2_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/test2.cpp'

        output = StringIO()
        self.plist_conv.write(output)

        with open('tidy2.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()

    def test_tidy3(self):
        """Test for the tidy3.plist file."""
        self.plist_conv.add_messages(self.tidy3_repr)

        # use relative path for this test
        self.plist_conv.plist['files'][0] = 'files/test3.cpp'
        self.plist_conv.plist['files'][1] = 'files/test3.hh'

        output = StringIO()
        self.plist_conv.write(output)

        with open('tidy3.plist') as pfile:
            exp = pfile.read()
            self.assertEqual(exp, output.getvalue())

        output.close()
