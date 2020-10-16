#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" skip function test.  """

import logging
import os
import plistlib
import unittest

from libtest.debug_printer import print_run_results
from libtest.thrift_client_to_db import get_all_run_results
from libtest.result_compare import find_all
from libtest import codechecker, env


class TestSkip(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        # Get the test configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace)

        runs = self._cc_client.getRunData(None, None, 0, None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         "There should be only one run for this test.")
        self._runid = test_runs[0].runId

    def test_skip(self):
        """ There should be no results from the skipped file. """

        runid = self._runid
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)

        skipped_files = ["file_to_be_skipped.cpp", "skip.h", "path_end.h"]

        # IMPORTANT: This test is checking whether some reports are really not
        # stored because they were skipped during analysis with --skip flag.
        # However, since clang-tidy is not run, there will be no reports from
        # "clang-diagnostic" checker. These are handled separately here,
        # otherwise the test would believe they're missing because of --skip
        # which is not the case.

        test_proj_res = self._testproject_data[self._clang_to_test]['bugs']
        skipped = [x for x in test_proj_res if x['file'] in skipped_files
                   or x['checker'].startswith('clang-diagnostic-')]

        print("Analysis:")
        for res in run_results:
            print(res)

        print("\nTest config results:")
        for res in test_proj_res:
            print(res)

        print("\nTest config skipped results:")
        for res in skipped:
            print(res)

        missing_results = find_all(run_results, test_proj_res)

        print_run_results(run_results)

        print('Missing results:')
        for mr in missing_results:
            print(mr)

        if missing_results:
            for bug in missing_results:
                if not bug['checker'].startswith('clang-diagnostic-'):
                    self.assertIn(bug['file'], skipped_files)
        else:
            self.assertTrue(True,
                            "There should be missing results because"
                            "using skip")

        self.assertEqual(len(run_results), len(test_proj_res) - len(skipped))

    def test_skip_plist_without_diag(self):
        """ Store plist file without diagnostics.

        Store plist file which does not contain any diagnostic but it refers
        some existing source file.
        """
        test_dir = os.path.join(self.test_workspace, "no_diag")
        if not os.path.isdir(test_dir):
            os.mkdir(test_dir)

        src_file = os.path.join(test_dir, "src.cpp")
        with open(src_file, 'w', encoding='utf-8', errors='ignore') as src_f:
            src_f.write("int main() { return 0; }")

        plist_file = os.path.join(test_dir, "no_diag.plist")
        with open(plist_file, 'wb') as plist_f:
            data = {
                'diagnostics': [],
                'files': [src_file]
            }
            plistlib.dump(data, plist_f)

        cfg = dict(self._codechecker_cfg)
        cfg['reportdir'] = test_dir

        ret = codechecker.store(cfg, 'no_diag')
        self.assertEqual(ret, 0)
