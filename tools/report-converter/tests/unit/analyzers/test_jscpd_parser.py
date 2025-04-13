# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform a Clang jscpd output file to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.jscpd import analyzer_result
from codechecker_report_converter.report.parser import plist


OLD_PWD = None


def setup_module():
    """Setup the test jscpd reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'jscpd_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class JscpdAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the JscpdAnalyzerResult. """

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

        print(f"RES: {res}")
        print(f"EXP: {exp}")

        self.assertEqual(res, exp)

    def test_jscpd(self):
        """ Test for the jscpd plist file. """
        self.__check_analyzer_result('jscpd-report.json',
                                     'duplicate1.c_jscpd.plist',
                                     ['files/duplicate1.c',
                                      'files/duplicate2.c'],
                                     'test_jscpd.plist')
