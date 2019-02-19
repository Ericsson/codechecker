#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Tests for source file changes
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os
import time
import unittest

from libtest import codechecker
from libtest import env


def touch(fname, times=None):
    """
    Modify the update and last modification times for a file.
    """
    with open(fname, 'a'):
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
        Test if parse there are skip messages in the output of the parse if
        the source files did change between the analysis and the parse.
        """

        test_proj_path = self._testproject_data['project_path']

        test_proj_files = os.listdir(test_proj_path)
        print(test_proj_files)

        null_deref_file = os.path.join(test_proj_path, 'null_dereference.cpp')

        codechecker.analyze(self._codechecker_cfg,
                            'hash_change',
                            test_proj_path)

        ret, out, _ = codechecker.parse(self._codechecker_cfg)
        self.assertEqual(ret, 0)

        # Need to wait a little before updating the last modification time.
        # If we do not wait, not enough time will be past
        # between the analysis and the parse in the test.
        time.sleep(2)
        touch(null_deref_file)

        ret, out, _ = codechecker.parse(self._codechecker_cfg)
        self.assertEqual(ret, 0)
        print(out)

        msg = 'did change since the last analysis.'
        self.assertTrue(msg in out,
                        '"' + msg + '" was not found in the parse output')

    def test_store(self):
        """
        Store should fail if the source files were modified since the
        last analysis.
        """

        test_proj = os.path.join(self.test_workspace, 'test_proj')

        ret = codechecker.check(self._codechecker_cfg,
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
