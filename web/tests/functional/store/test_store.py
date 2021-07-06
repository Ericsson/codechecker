#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
store tests.
"""


import json
import os
import shlex
import inspect
import plistlib
import shutil
import subprocess
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import AnalysisInfoFilter
from libtest import codechecker, env

from codechecker_common import util


def _call_cmd(command, cwd=None, env=None):
    try:
        print(' '.join(command))
        proc = subprocess.Popen(
            shlex.split(' '.join(command)),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env, encoding="utf-8", errors="ignore")
        out, err = proc.communicate()
        return proc.returncode, out, err
    except subprocess.CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode, None, None


class TestStore(unittest.TestCase):
    """Test storage reports"""

    def setUp(self):

        # Get the test workspace used to cppcheck tests.
        self._test_workspace = os.environ["TEST_WORKSPACE"]

        test_class = self.__class__.__name__
        print("Running " + test_class + " tests in " + self._test_workspace)

        self._test_cfg = env.import_test_cfg(self._test_workspace)
        self._codechecker_cfg = self._test_cfg["codechecker_cfg"]
        self._test_directory = os.path.dirname(os.path.abspath(inspect.getfile(
            inspect.currentframe())))
        self._temp_workspace = os.path.join(self._codechecker_cfg["workspace"],
                                            "test_proj")

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

    def test_trim_path_prefix_store(self):
        """Trim the path prefix from the sored reports.

        The source file paths are converted to absolute with the
        temporary test directory, the test trims that temporary
        test directory from the source file path during the storage.
        """
        report_file = os.path.join(self._temp_workspace, "divide_zero.plist")

        report_content = {}
        with open(report_file, mode="rb") as rf:
            report_content = plistlib.load(rf)

        trimmed_paths = [
            util.trim_path_prefixes(path, [self._temp_workspace])
            for path in report_content["files"]
        ]

        run_name = "store_test"
        store_cmd = [
            env.codechecker_cmd(),
            "store",
            self._temp_workspace,
            "--name",
            run_name,
            "--url",
            env.parts_to_url(self._codechecker_cfg),
            "--trim-path-prefix",
            self._temp_workspace,
            "--verbose",
            "debug",
        ]

        ret, _, _ = _call_cmd(store_cmd)
        self.assertEqual(ret, 0, "Plist file could not store.")

        query_cmd = [
            env.codechecker_cmd(),
            "cmd",
            "results",
            run_name,
            # Use the 'Default' product.
            "--url",
            env.parts_to_url(self._codechecker_cfg),
            "-o",
            "json",
        ]

        ret, out, _ = _call_cmd(query_cmd)
        self.assertEqual(ret, 0, "Could not read from server.")
        reports = json.loads(out)

        print(json.dumps(reports, indent=2))

        self.assertEqual(len(reports), 4)
        for report in reports:
            self.assertIn(report["checkedFile"], trimmed_paths)

    def test_store_multiple_report_dirs(self):
        """ Test storing multiple report directories.

        Analyze the same project to different report directories with different
        checker configurations and store these report directories with one
        store command to a run.
        """
        cfg = dict(self._codechecker_cfg)
        codechecker.log(cfg, self._temp_workspace)

        common_report_dir = os.path.join(self._temp_workspace, 'reports')
        report_dir1 = \
            os.path.join(self._temp_workspace, common_report_dir,
                         'report_dir1')
        report_dir2 = \
            os.path.join(self._temp_workspace, common_report_dir,
                         'report_dir2')

        cfg['reportdir'] = report_dir1
        cfg['checkers'] = [
            '-d', 'core.DivideZero', '-e', 'deadcode.DeadStores']
        codechecker.analyze(cfg, self._temp_workspace)

        cfg['reportdir'] = report_dir2
        cfg['checkers'] = [
            '-e', 'core.DivideZero', '-d', 'deadcode.DeadStores']
        codechecker.analyze(cfg, self._temp_workspace)

        def store_multiple_report_dirs(report_dirs):
            """ """
            run_name = "multiple_report_dirs"
            store_cmd = [
                env.codechecker_cmd(), "store",
                *report_dirs,
                "--name", run_name,
                "--url", env.parts_to_url(self._codechecker_cfg)]

            proc = subprocess.Popen(
                store_cmd, encoding="utf-8", errors="ignore",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, err = proc.communicate()

            self.assertNotIn("UserWarning: Duplicate name", err)

            # Check the reports.
            query_cmd = [
                env.codechecker_cmd(), "cmd", "results",
                run_name,
                "--url", env.parts_to_url(self._codechecker_cfg),
                "-o", "json"]

            out = subprocess.check_output(
                query_cmd, encoding="utf-8", errors="ignore")
            reports = json.loads(out)

            self.assertTrue(
                any(r['checkerId'] == 'core.DivideZero' for r in reports))

            self.assertTrue(
                any(r['checkerId'] == 'deadcode.DeadStores' for r in reports))

            # Get analysis info.
            limit = None
            offset = 0
            report = [r for r in reports
                      if r['checkerId'] == 'core.DivideZero'][0]

            # Get analysis info for a run.
            analysis_info_filter = AnalysisInfoFilter(runId=report['runId'])
            analysis_info = self._cc_client.getAnalysisInfo(
                analysis_info_filter, limit, offset)
            self.assertEqual(len(analysis_info), 2)
            self.assertTrue(
                any(report_dir1 in i.analyzerCommand for i in analysis_info))
            self.assertTrue(
                any(report_dir2 in i.analyzerCommand for i in analysis_info))

            # Get analysis info for a report.
            analysis_info_filter = AnalysisInfoFilter(
                reportId=report['reportId'])

            analysis_info = self._cc_client.getAnalysisInfo(
                analysis_info_filter, limit, offset)
            self.assertEqual(len(analysis_info), 1)
            self.assertTrue(
                any(report_dir2 in i.analyzerCommand for i in analysis_info))

            # Get analysis infor for run history.
            query_cmd = [
                env.codechecker_cmd(), "cmd", "history",
                "-n", run_name,
                "--url", env.parts_to_url(self._codechecker_cfg),
                "-o", "json"]

            out = subprocess.check_output(
                query_cmd, encoding="utf-8", errors="ignore")
            history = json.loads(out)
            self.assertTrue(history)

            h = max(history, key=lambda h: h["id"])

            analysis_info_filter = AnalysisInfoFilter(runHistoryId=h['id'])
            analysis_info = self._cc_client.getAnalysisInfo(
                analysis_info_filter, limit, offset)
            self.assertEqual(len(analysis_info), 2)
            self.assertTrue(
                any(report_dir1 in i.analyzerCommand for i in analysis_info))
            self.assertTrue(
                any(report_dir2 in i.analyzerCommand for i in analysis_info))

            # Check the reports.
            rm_cmd = [
                env.codechecker_cmd(), "cmd", "del",
                "-n", run_name,
                "--url", env.parts_to_url(self._codechecker_cfg)]

            out = subprocess.check_output(
                rm_cmd, encoding="utf-8", errors="ignore")

        # Store report directories separately.
        store_multiple_report_dirs([report_dir1, report_dir2])

        # Store report directories recursively.
        store_multiple_report_dirs([common_report_dir])

        shutil.rmtree(common_report_dir, ignore_errors=True)

    def test_duplicated_suppress(self):
        """
        Test server if recognise duplicated suppress comments in the stored
        source code.
        """

        test_plist_file = "double_suppress.plist"

        store_cmd = [env.codechecker_cmd(), "store", "--url",
                     env.parts_to_url(self._codechecker_cfg), "--name",
                     "never",  "--input-format", "plist",
                     "--verbose", "debug", test_plist_file]

        ret, _, _ = _call_cmd(store_cmd, self._temp_workspace)
        self.assertEqual(ret, 1, "Duplicated suppress comments was not "
                         "recognised.")
