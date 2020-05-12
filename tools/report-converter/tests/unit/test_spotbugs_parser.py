# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the SpotBugsAnalyzerResult, which
used in sequence transform SpotBugs output to a plist file.
"""

import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.spotbugs.analyzer_result import \
    SpotBugsAnalyzerResult


OLD_PWD = None


def setup_module():
    """ Setup the test. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'spotbugs_output_test_files'))


def teardown_module():
    """ Restore environment after tests have ran. """
    global OLD_PWD
    os.chdir(OLD_PWD)


class SpotBugsAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the SpotBugsAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = SpotBugsAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'spotbugs_output_test_files')

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_no_xml_file(self):
        """ Test transforming single non xml file. """
        analyzer_result = os.path.join(self.test_files, 'files',
                                       'Assign.java')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_parsing_dir(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'files')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertFalse(ret)

    def test_transform_single_file(self):
        """ Test transforming single plist file. """
        analyzer_result = os.path.join(self.test_files, 'assign.xml')
        self.analyzer_result.transform(analyzer_result, self.cc_result_dir)

        plist_file = os.path.join(self.cc_result_dir,
                                  'Assign.java_spotbugs.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'assign.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
