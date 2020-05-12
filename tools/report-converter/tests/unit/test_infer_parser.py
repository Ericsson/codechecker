# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This module tests the correctness of the InferAnalyzerResult, which
used in sequence transform Infer output to a plist file.
"""

import os
import plistlib
import shutil
import tempfile
import unittest

from codechecker_report_converter.infer.analyzer_result import \
    InferAnalyzerResult


OLD_PWD = None


def setup_module():
    """ Setup the test. """
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'infer_output_test_files'))


def teardown_module():
    """ Restore environment after tests have ran. """
    global OLD_PWD
    os.chdir(OLD_PWD)


class InferAnalyzerResultTestCase(unittest.TestCase):
    """ Test the output of the InferAnalyzerResult. """

    def setUp(self):
        """ Setup the test. """
        self.analyzer_result = InferAnalyzerResult()
        self.cc_result_dir = tempfile.mkdtemp()
        self.test_files = os.path.join(os.path.dirname(__file__),
                                       'infer_output_test_files')

    def tearDown(self):
        """ Clean temporary directory. """
        shutil.rmtree(self.cc_result_dir)

    def test_parsing_cpp_res_dir(self):
        """ Test transforming infer output directory (C++). """
        analyzer_result = os.path.join(self.test_files, 'infer-out-dead_store')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertTrue(ret)

        plist_file = os.path.join(self.cc_result_dir,
                                  'dead_store.cpp_fbinfer.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'dead_store.cpp.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    def test_transform_single_cpp_res_file(self):
        """ Test transforming single infer report file (C++). """
        analyzer_result = os.path.join(self.test_files,
                                       'infer-out-dead_store',
                                       'report.json')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertTrue(ret)

        plist_file = os.path.join(self.cc_result_dir,
                                  'dead_store.cpp_fbinfer.plist')
        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'dead_store.cpp.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    def test_parsing_java_res_dir(self):
        """ Test transforming infer output directory (Java). """
        analyzer_result = os.path.join(self.test_files,
                                       'infer-out-null_dereference')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertTrue(ret)

        plist_file = os.path.join(self.cc_result_dir,
                                  'NullDereference.java_fbinfer.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'NullDereference.java.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)

    def test_transform_single_java_res_file(self):
        """ Test transforming single infer report file (Java). """
        analyzer_result = os.path.join(self.test_files,
                                       'infer-out-null_dereference',
                                       'report.json')

        ret = self.analyzer_result.transform(analyzer_result,
                                             self.cc_result_dir)
        self.assertTrue(ret)

        plist_file = os.path.join(self.cc_result_dir,
                                  'NullDereference.java_fbinfer.plist')

        with open(plist_file, mode='rb') as pfile:
            res = plistlib.load(pfile)

            self.assertTrue(res['metadata']['generated_by']['version'])
            res['metadata']['generated_by']['version'] = "x.y.z"

        plist_file = os.path.join(self.test_files,
                                  'NullDereference.java.plist')
        with open(plist_file, mode='rb') as pfile:
            exp = plistlib.load(pfile)

        self.assertEqual(res, exp)
