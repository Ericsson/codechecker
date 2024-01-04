# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform UndefinedBehaviorSanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.sanitizers.ub import \
    analyzer_result
from codechecker_report_converter.report.parser import plist

OLD_PWD = None


def setup_module():
    """ Setup the test tidy reprs for the test classes in the module. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'ubsan_output_test_files'))


def teardown_module():
    """ Restore environment after tests have ran. """
    global OLD_PWD
    os.chdir(OLD_PWD)


class UBSANPListConverterTestCase(unittest.TestCase):
    """ Test the output of the UBSANAnalyzerResult. """

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

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        with open(expected_plist, mode='rb') as pfile:
            exp = plistlib.load(pfile)

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

    def test_ubsan1(self):
        """ Test for the ubsan1.plist file. """
        self.__check_analyzer_result('ubsan1.out', 'ubsan1.cpp_ubsan.plist',
                                     ['files/ubsan1.cpp'], 'ubsan1.plist')

    def test_ubsan1_nonmatching_msg(self):
        """
        Test for the test_ubsan1_nonmatching_msg.plist file, where the reported
        error message doesn't match any of the checkers we recognize.
        """
        self.maxDiff = None
        self.__check_analyzer_result(
            'ubsan1_nonmatching_msg.out', 'ubsan1.cpp_ubsan.plist',
            ['files/ubsan1.cpp'], 'ubsan1_nonmatching_msg.plist')

    def test_ubsan2(self):
        """ Test for the ubsan2.plist file. """
        self.__check_analyzer_result('ubsan2.out', 'ubsan2.cpp_ubsan.plist',
                                     ['files/ubsan2.cpp'], 'ubsan2.plist')
