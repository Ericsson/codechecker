# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the clazy AnalyzerResult, which is used
to transform clazy-standalone console output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.clazy import analyzer_result
from codechecker_report_converter.report.parser import plist


OLD_PWD = None


def setup_module():
    """ Setup the test. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'clazy_output_test_files'))


def teardown_module():
    """ Restore environment after tests have ran. """
    if OLD_PWD:
        os.chdir(OLD_PWD)


class ClazyAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the clazy AnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_empty(self):
        """ Test for an output without any warnings. """
        ret = self.analyzer_result.transform(
            ['empty.out'], self.cc_result_dir, plist.EXTENSION)
        self.assertFalse(ret)

    def test_reports(self):
        """ Test the reports parsed from a real clazy-standalone output. """
        reports = self.analyzer_result.get_reports('main.out')

        self.assertEqual(
            [(os.path.relpath(r.file.path), r.line, r.column,
              r.checker_name, r.message) for r in reports],
            [('files/main.cpp', 8, 5, 'clazy-old-style-connect',
              'Old Style Connect'),
             ('files/value.h', 4, 1, 'clazy-rule-of-three',
              'Value has dtor, copy-ctor but not copy-assignment'),
             ('files/main.cpp', 16, 5, 'clazy-container-anti-pattern',
              'allocating an unneeded temporary container'),
             ('files/main.cpp', 16, 5, 'clazy-range-loop-detach',
              'c++11 range-loop might detach Qt container (QList)'),
             ('files/main.cpp', 23, 17, 'clazy-qstring-allocations',
              'QString(const char*) being called')])

    def test_include_stack_and_summary_are_not_notes(self):
        """
        The "In file included from" and "N warnings generated." lines must
        not be turned into fixit notes.
        """
        reports = self.analyzer_result.get_reports('main.out')

        self.assertEqual(
            [[n.message for n in r.notes] for r in reports],
            [['&QTimer::timeout             &QObject::deleteLater (fixit)'],
             [],
             [],
             [],
             ['QStringLiteral( ) (fixit)']])

    def test_compiler_diagnostics(self):
        """
        Compiler warnings are named like Clang-Tidy names them and compile
        errors, which have no checker name in the output, become
        clang-diagnostic-error reports. The "Error while processing" line
        must not be turned into a note.
        """
        reports = self.analyzer_result.get_reports('compile_error.out')

        self.assertEqual(
            [(os.path.relpath(r.file.path), r.line, r.column,
              r.checker_name, r.message, [n.message for n in r.notes])
             for r in reports],
            [('files/compile_error.cpp', 5, 9,
              'clang-diagnostic-unused-variable',
              "unused variable 'unused'", []),
             ('files/compile_error.cpp', 12, 12, 'clang-diagnostic-error',
              "use of undeclared identifier 'missing'; did you mean 'using'?",
              ['using (fixit)']),
             ('files/compile_error.cpp', 12, 12, 'clang-diagnostic-error',
              'expected expression', [])])

    def test_fatal_error(self):
        """ A missing header is reported as a clang-diagnostic-error. """
        reports = self.analyzer_result.get_reports('missing_include.out')

        self.assertEqual(
            [(os.path.relpath(r.file.path), r.line, r.column,
              r.checker_name, r.message, [n.message for n in r.notes])
             for r in reports],
            [('files/missing_include.cpp', 2, 10, 'clang-diagnostic-error',
              "'does_not_exist.h' file not found", [])])

    def test_werror(self):
        """
        A warning turned into an error by -Werror gives a single report
        with the name of the warning.
        """
        reports = self.analyzer_result.get_reports('werror.out')

        self.assertEqual(
            [(r.line, r.checker_name, r.message) for r in reports],
            [(5, 'clang-diagnostic-unused-variable',
              "unused variable 'unused'"),
             (12, 'clang-diagnostic-error',
              "use of undeclared identifier 'missing'; did you mean 'using'?"),
             (12, 'clang-diagnostic-error', 'expected expression')])

    def test_transform(self):
        """ Test transforming a clazy output to plist files. """
        ret = self.analyzer_result.transform(
            ['main.out'], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")
        self.assertTrue(ret)

        self.assertEqual(
            sorted(os.listdir(self.cc_result_dir)),
            ['main.cpp_clazy.plist', 'value.h_clazy.plist'])

        plist_file = os.path.join(self.cc_result_dir, 'main.cpp_clazy.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

        self.assertEqual(
            [d['check_name'] for d in res['diagnostics']],
            ['clazy-old-style-connect', 'clazy-container-anti-pattern',
             'clazy-range-loop-detach', 'clazy-qstring-allocations'])
        self.assertEqual(res['metadata']['analyzer']['name'], 'clazy')
