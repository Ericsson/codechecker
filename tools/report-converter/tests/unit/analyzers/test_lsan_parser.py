# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the OutputParser and PListConverter, which
used in sequence transform LeakSanitizer output to a plist file.
"""


import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.analyzers.sanitizers.leak import \
    analyzer_result
from codechecker_report_converter.report.parser import plist


OLD_PWD = None


def setup_module():
    """Setup the test tidy reprs for the test classes in the module."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'lsan_output_test_files'))


def teardown_module():
    """Restore environment after tests have ran."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class LSANPListConverterTestCase(unittest.TestCase):
    """ Test the output of the LSANAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = analyzer_result.AnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_san(self):
        """ Test for the lsan.plist file. """
        self.analyzer_result.transform(
            'lsan.out', self.cc_result_dir, plist.EXTENSION)

        with open('lsan.plist', mode='rb') as pfile:
            exp = plistlib.load(pfile)

        plist_file = os.path.join(self.cc_result_dir, 'lsan.c_lsan.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            # Use relative path for this test.
            res['files'][0] = 'files/lsan.c'

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        self.assertEqual(res, exp)
