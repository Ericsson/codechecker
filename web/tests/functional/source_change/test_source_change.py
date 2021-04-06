#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Tests for source file changes
"""


import os
import time
import unittest

from libtest import codechecker
from libtest import env


def touch(fname, times=None):
    """
    Modify the update and last modification times for a file.
    """
    with open(fname, 'a', encoding="utf-8", errors="ignore"):
        os.utime(fname, times)


class TestSkeleton(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        self.env = env.codechecker_env()

    def test_parse(self):
        """
        Test if there are skip messages in the output of the parse command if
        the source files did change between the analysis and the parse.
        """

        test_proj_path = self._testproject_data['project_path']

        test_proj_files = os.listdir(test_proj_path)
        print(test_proj_files)

        null_deref_file = os.path.join(test_proj_path, 'null_dereference.cpp')

        codechecker.log_and_analyze(self._codechecker_cfg,
                                    test_proj_path)

        ret, out, _ = codechecker.parse(self._codechecker_cfg)
        self.assertEqual(ret, 2)

        # Need to wait a little before updating the last modification time.
        # If we do not wait, not enough time will be past
        # between the analysis and the parse in the test.
        time.sleep(2)
        touch(null_deref_file)

        ret, out, _ = codechecker.parse(self._codechecker_cfg)
        self.assertEqual(ret, 2)

        msg = 'did change since the last analysis.'
        self.assertTrue(msg in out,
                        '"' + msg + '" was not found in the parse output')

    def test_store(self):
        """
        Store should fail if the source files were modified since the
        last analysis.
        """

        test_proj = os.path.join(self.test_workspace, 'test_proj')

        ret = codechecker.check_and_store(self._codechecker_cfg,
                                          'test_proj',
                                          test_proj)

        self.assertEqual(ret, 0)

        ret = codechecker.store(self._codechecker_cfg, 'test_proj')
        self.assertEqual(ret, 0)

        test_proj_path = self._testproject_data['project_path']

        test_proj_files = os.listdir(test_proj_path)
        print(test_proj_files)

        null_deref_file = os.path.join(test_proj_path, 'null_dereference.cpp')

        touch(null_deref_file)

        ret = codechecker.store(self._codechecker_cfg, 'test_proj')
        self.assertEqual(ret, 1)

    def test_store_config_file_mod(self):
        """Storage should be successful if a non report related file changed.

        Checking the modification time stamps should be done only for
        the source files mentioned in the report plist files.
        Modifying any non report related file should not prevent the storage
        of the reports.
        """
        test_proj = os.path.join(self.test_workspace, 'test_proj')

        ret = codechecker.log(self._codechecker_cfg, test_proj,
                              clean_project=True)
        self.assertEqual(ret, 0)

        ret = codechecker.analyze(self._codechecker_cfg, test_proj)
        self.assertEqual(ret, 0)

        test_proj_path = self._testproject_data['project_path']

        # touch one file so it will be analyzed again
        touch(os.path.join(test_proj_path, 'null_dereference.cpp'))

        ret = codechecker.log(self._codechecker_cfg, test_proj)
        self.assertEqual(ret, 0)

        ret = codechecker.analyze(self._codechecker_cfg,
                                  test_proj)
        self.assertEqual(ret, 0)

        touch(os.path.join(self._codechecker_cfg['reportdir'],
                           'compile_cmd.json'))

        ret = codechecker.store(self._codechecker_cfg, 'test_proj')
        self.assertEqual(ret, 0)
