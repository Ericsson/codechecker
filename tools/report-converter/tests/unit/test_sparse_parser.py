# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform a Sparse output file to a plist file.
"""


import os
import unittest

from codechecker_report_converter.output_parser import Message, Event
from codechecker_report_converter.sparse.output_parser import \
    SparserParser
from codechecker_report_converter.sparse.analyzer_result import \
    SparseAnalyzerResult

OLD_PWD = None


def setup_module():
    """Setup the test sparse reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), 'sparse_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class SparseOutputParserTestCase(unittest.TestCase):
    """
    Tests the output of the OutputParser, which converts a Sparse output
    file to zero or more sparse_output_converter.Message.
    """

    def setUp(self):
        """Setup the OutputParser.""" 
        self.parser = SparserParser()
 
        # sparse1.out detailed Message representation
        self.sparse1_repr = 
            Message(
                os.path.abspath('kernel/trace/trace.h'),
                1499, 38,
                'incorrect type in argument 1 (different address spaces) '
                + 'expected struct event_filter *filter '
                + 'got struct event_filter [noderef] __rcu *filter')

        # sparse2.out simple message representation
        self.sparse2_repr =
            Message(
                os.path.abspath('kernel/trace/bpf_trace.c'),
                161, 29,
                "symbol 'bpf_probe_read_user_proto' was not declared. Should it be static?")

    def test_sparse_detailed_message(self):
        """Test the generated Messages of sparse1.out Sparse output file."""
        messages = self.parser.parse_messages_from_file('sparse1.out')
        self.assertEqual(len(messages), len(self.sparse1_repr))
        for message in messages:
            self.assertIn(message, self.tidy1_repr)

    def test_sparse_simple_message(self):
        """Test the generated Messages of sparse2.out Sparse output file."""
        messages = self.parser.parse_messages_from_file('sparse2.out')
        self.assertEqual(len(messages), len(self.tidy1_repr))
        for message in messages:
            self.assertIn(message, self.tidy1_repr)
