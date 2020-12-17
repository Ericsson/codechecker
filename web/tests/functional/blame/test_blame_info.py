#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Blame info function test. """


import json
import os
import tempfile
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Order, \
  ReportFilter, RunFilter, RunSortMode, RunSortType
from libtest.thrift_client_to_db import get_all_run_results

from libtest import codechecker
from libtest import env


class TestBlameInfo(unittest.TestCase):

    def setUp(self):
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._test_dir = os.path.join(self.test_workspace, 'test_files')
        self._run_name = 'hello'

        try:
            os.makedirs(self._test_dir)
        except os.error:
            # Directory already exists.
            pass

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        self.test_runs = self._cc_client.getRunData(None, None, 0, sort_mode)

    def test_no_blame_info(self):
        """ Test if the source file doesn't have any blame information. """
        with tempfile.TemporaryDirectory() as proj_dir:
            source_file_name = "no_blame.cpp"
            src_file = os.path.join(proj_dir, source_file_name)

            with open(os.path.join(proj_dir, 'Makefile'), 'w',
                      encoding="utf-8", errors="ignore") as f:
                f.write(f"all:\n\t$(CXX) -c {src_file} -o /dev/null\n")

            with open(os.path.join(proj_dir, 'project_info.json'), 'w',
                      encoding="utf-8", errors="ignore") as f:
                json.dump({
                    "name": "hello",
                    "clean_cmd": "",
                    "build_cmd": "make"}, f)

            with open(src_file, 'w', encoding="utf-8", errors="ignore") as f:
                f.write("int main() { sizeof(42); }")

            # Change working dir to testfile dir so CodeChecker can be run
            # easily.
            old_pwd = os.getcwd()
            os.chdir(proj_dir)

            run_name = "no_blame_info"
            codechecker.check_and_store(
                self._codechecker_cfg, run_name, proj_dir)

            os.chdir(old_pwd)

            run_filter = RunFilter(names=[run_name], exactMatch=True)
            runs = self._cc_client.getRunData(run_filter, None, 0, None)
            run_id = runs[0].runId

            report_filter = ReportFilter(
                checkerName=['*'],
                filepath=[f'*{source_file_name}'])

            run_results = get_all_run_results(
                self._cc_client, run_id, [], report_filter)
            self.assertIsNotNone(run_results)

            report = run_results[0]

            # Get source file data.
            file_data = self._cc_client.getSourceFileData(
                report.fileId, True, None)
            self.assertIsNotNone(file_data)
            self.assertFalse(file_data.hasBlameInfo)
            self.assertFalse(file_data.remoteUrl)
            self.assertFalse(file_data.trackingBranch)

            # Get blame information
            blame_info = self._cc_client.getBlameInfo(report.fileId)
            self.assertIsNotNone(blame_info)
            self.assertFalse(blame_info.commits)
            self.assertFalse(blame_info.blame)

    def test_get_blame_info(self):
        """ Get blame information for a source file. """
        runid = self.test_runs[0].runId
        report_filter = ReportFilter(
            checkerName=['*'],
            filepath=['*call_and_message.cpp*'])

        run_results = get_all_run_results(
            self._cc_client, runid, [], report_filter)
        self.assertIsNotNone(run_results)

        report = run_results[0]

        # Get source file data.
        file_data = self._cc_client.getSourceFileData(
            report.fileId, True, None)
        self.assertIsNotNone(file_data)
        self.assertTrue(file_data.hasBlameInfo)
        self.assertTrue(file_data.remoteUrl)
        self.assertTrue(file_data.trackingBranch)

        # Get blame information
        blame_info = self._cc_client.getBlameInfo(report.fileId)
        self.assertIsNotNone(blame_info)
        self.assertTrue(len(blame_info.commits))
        self.assertTrue(len(blame_info.blame))
