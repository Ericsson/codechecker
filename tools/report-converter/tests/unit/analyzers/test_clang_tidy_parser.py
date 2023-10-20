# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform a Clang Tidy output file to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.clang_tidy import analyzer_result
from codechecker_report_converter.report.parser import plist


OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), 'tidy_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class ClangTidyAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the ClangTidyAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def __check_analyzer_result(self, analyzer_result, analyzer_result_plist,
                                source_files, expected_plist):
        """ Check the result of the analyzer transformation. """
        self.analyzer_result.transform(
            [analyzer_result], self.cc_result_dir, plist.EXTENSION,
            file_name="{source_file}_{analyzer}")

        plist_file = os.path.join(self.cc_result_dir, analyzer_result_plist)
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'] = source_files

        with open(expected_plist, mode='rb') as pfile:
            exp = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)

    def test_empty1(self):
        """ Test for empty Messages. """
        ret = self.analyzer_result.transform(
            ['empty1.out'], self.cc_result_dir, plist.EXTENSION)
        self.assertFalse(ret)

    def test_empty2(self):
        """ Test for empty Messages with multiple line. """
        ret = self.analyzer_result.transform(
            ['empty2.out'], self.cc_result_dir, plist.EXTENSION)
        self.assertFalse(ret)

    def test_tidy1(self):
        """ Test for the tidy1.plist file. """
        self.__check_analyzer_result('tidy1.out', 'test.cpp_clang-tidy.plist',
                                     ['files/test.cpp'], 'tidy1.plist')

    def test_tidy2(self):
        """ Test for the tidy2.plist file. """
        self.__check_analyzer_result('tidy2.out', 'test2.cpp_clang-tidy.plist',
                                     ['files/test2.cpp'], 'tidy2.plist')

    def test_tidy3(self):
        """ Test for the tidy3.plist file. """
        self.__check_analyzer_result('tidy3.out', 'test3.cpp_clang-tidy.plist',
                                     ['files/test3.cpp'],
                                     'tidy3_cpp.plist')

        self.__check_analyzer_result('tidy3.out', 'test3.hh_clang-tidy.plist',
                                     ['files/test3.cpp', 'files/test3.hh'],
                                     'tidy3_hh.plist')

        self.__check_analyzer_result('tidy3-clang17.out',
                                     'test3.hh_clang-tidy.plist',
                                     ['files/test3.cpp', 'files/test3.hh'],
                                     'tidy3_hh.plist')
