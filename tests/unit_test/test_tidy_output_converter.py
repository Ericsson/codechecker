#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import os
import unittest
import copy
import StringIO

from codechecker_lib.tidy_output_converter import *

os.chdir(os.path.join(os.path.dirname(__file__), 'tidy_output_files'))

# tidy1.out Message/Note representation
TIDY1_TIDY_REPR = [
    Message(os.path.abspath('files/test.cpp'),
            8, 12,
            'Division by zero',
            'clang-analyzer-core.DivideZero',
            None,
            [Note(os.path.abspath('files/test.cpp'),
                  8, 12,
                  'Division by zero')]),
    Message(os.path.abspath('files/test.cpp'),
            8, 12,
            'remainder by zero is undefined',
            'clang-diagnostic-division-by-zero')
]

# tidy2.out Message/Note representation
TIDY2_TIDY_REPR = [
    Message(os.path.abspath('files/test2.cpp'),
            5, 7,
            "unused variable 'y'",
            'clang-diagnostic-unused-variable'),
    Message(os.path.abspath('files/test2.cpp'),
            13, 12,
            'Division by zero',
            'clang-analyzer-core.DivideZero',
            None,
            [Note(os.path.abspath('files/test2.cpp'),
                  9, 7,
                  "Left side of '||' is false"),
             Note(os.path.abspath('files/test2.cpp'),
                  9, 3,
                  'Taking false branch'),
             Note(os.path.abspath('files/test2.cpp'),
                  13, 12,
                  'Division by zero')]),
    Message(os.path.abspath('files/test2.cpp'),
            13, 12,
            'remainder by zero is undefined',
            'clang-diagnostic-division-by-zero'),
]

# tidy3.out Message/Note representation
TIDY3_TIDY_REPR = [
    Message(os.path.abspath('files/test3.cpp'),
            4, 12,
            'use nullptr',
            'modernize-use-nullptr',
            [Note(os.path.abspath('files/test3.cpp'),
             4, 12,
             'nullptr')]),
    Message(os.path.abspath('files/test3.hh'),
            6, 6,
            "Dereference of null pointer (loaded from variable 'x')",
            'clang-analyzer-core.NullDereference',
            None,
            [Note(os.path.abspath('files/test3.cpp'),
                  4, 3,
                  "'x' initialized to a null pointer value"),
             Note(os.path.abspath('files/test3.cpp'),
                  6, 11,
                  "Assuming 'argc' is > 3"),
             Note(os.path.abspath('files/test3.cpp'),
                  6, 3,
                  'Taking true branch'),
             Note(os.path.abspath('files/test3.cpp'),
                  7, 9,
                  "Passing null pointer value via 1st parameter 'x'"),
             Note(os.path.abspath('files/test3.cpp'),
                  7, 5,
                  "Calling 'bar'"),
             Note(os.path.abspath('files/test3.hh'),
                  6, 6,
                  "Dereference of null pointer (loaded from variable 'x')")])
]


class TidyOutputParserTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = OutputParser()


    def test_absolute_path(self):
        for file in ['abs.out', 'tidy1.out']:
            messages = self.parser.parse_messages_from_file(file)
            self.assertNotEqual(len(messages), 0)
            for message in messages:
                self.assertTrue(os.path.isabs(message.path))


    def test_empty1(self):
        messages = self.parser.parse_messages_from_file('empty1.out')
        self.assertEqual(messages, [])


    def test_empty2(self):
        messages = self.parser.parse_messages_from_file('empty2.out')
        self.assertEqual(messages, [])


    def test_tidy1(self):
        messages = self.parser.parse_messages_from_file('tidy1.out')
        self.assertEqual(len(messages), len(TIDY1_TIDY_REPR))
        for message in messages:
            self.assertIn(message, TIDY1_TIDY_REPR)


    def test_tidy2(self):
        messages = self.parser.parse_messages_from_file('tidy2.out')
        self.assertEqual(len(messages), len(TIDY2_TIDY_REPR))
        for message in messages:
            self.assertIn(message, TIDY2_TIDY_REPR)


    def test_tidy3(self):
        messages = self.parser.parse_messages_from_file('tidy3.out')
        self.assertEqual(len(messages), len(TIDY3_TIDY_REPR))
        for message in messages:
            self.assertIn(message, TIDY3_TIDY_REPR)


class TidyPListConverterTestCase(unittest.TestCase):

    def setUp(self):
        self.conv = PListConverter()

    def test_empty(self):
        orig_plist = copy.deepcopy(self.conv.plist)

        self.conv.add_messages([])
        self.assertDictEqual(orig_plist, self.conv.plist)

        output = StringIO.StringIO()
        self.conv.write(output)

        with open('empty.plist') as file:
            exp = file.read()
            self.assertEqual(exp, output.getvalue())

        output.close()


    def test_tidy1(self):
        self.conv.add_messages(TIDY1_TIDY_REPR)

        # use relative path for this test
        self.conv.plist['files'][0] = 'files/test.cpp'

        output = StringIO.StringIO()
        self.conv.write(output)

        with open('tidy1.plist') as file:
            exp = file.read()
            self.assertEqual(exp, output.getvalue())

        output.close()

    def test_tidy2(self):
        self.conv.add_messages(TIDY2_TIDY_REPR)

        # use relative path for this test
        self.conv.plist['files'][0] = 'files/test2.cpp'

        output = StringIO.StringIO()
        self.conv.write(output)

        with open('tidy2.plist') as file:
            exp = file.read()
            self.assertEqual(exp, output.getvalue())

        output.close()


    def test_tidy3(self):
        self.conv.add_messages(TIDY3_TIDY_REPR)

        # use relative path for this test
        self.conv.plist['files'][0] = 'files/test3.cpp'
        self.conv.plist['files'][1] = 'files/test3.hh'

        output = StringIO.StringIO()
        self.conv.write(output)

        with open('tidy3.plist') as file:
            exp = file.read()
            self.assertEqual(exp, output.getvalue())

        output.close()
