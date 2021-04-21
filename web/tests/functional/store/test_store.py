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
import plistlib
import shutil
import subprocess
import unittest

from libtest import codechecker
from libtest import env

from codechecker_common import util


class TestStore(unittest.TestCase):
    """Test storage reports"""

    def setUp(self):

        # Get the test workspace used to cppcheck tests.
        self._test_workspace = os.environ["TEST_WORKSPACE"]

        test_class = self.__class__.__name__
        print("Running " + test_class + " tests in " + self._test_workspace)

        self._test_cfg = env.import_test_cfg(self._test_workspace)
        self.codechecker_cfg = self._test_cfg["codechecker_cfg"]
        self.test_proj_dir = os.path.join(
            self.codechecker_cfg["workspace"], "test_proj")

    def test_trim_path_prefix_store(self):
        """Trim the path prefix from the sored reports.

        The source file paths are converted to absolute with the
        temporary test directory, the test trims that temporary
        test directory from the source file path during the storage.
        """
        report_file = os.path.join(self.test_proj_dir, "divide_zero.plist")

        report_content = {}
        with open(report_file, mode="rb") as rf:
            report_content = plistlib.load(rf)

        trimmed_paths = [
            util.trim_path_prefixes(path, [self.test_proj_dir])
            for path in report_content["files"]
        ]

        run_name = "store_test"
        store_cmd = [
            env.codechecker_cmd(),
            "store",
            self.test_proj_dir,
            "--name",
            run_name,
            "--url",
            env.parts_to_url(self.codechecker_cfg),
            "--trim-path-prefix",
            self.test_proj_dir,
            "--verbose",
            "debug",
        ]

        try:
            out = subprocess.check_output(
                store_cmd, encoding="utf-8", errors="ignore"
            )
            print(out)
        except subprocess.CalledProcessError as cerr:
            print(cerr.stdout)
            print(cerr.stderr)
            raise

        query_cmd = [
            env.codechecker_cmd(),
            "cmd",
            "results",
            run_name,
            # Use the 'Default' product.
            "--url",
            env.parts_to_url(self.codechecker_cfg),
            "-o",
            "json",
        ]

        out = subprocess.check_output(
            query_cmd, encoding="utf-8", errors="ignore"
        )
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
        cfg = dict(self.codechecker_cfg)
        codechecker.log(cfg, self.test_proj_dir)

        common_report_dir = os.path.join(self.test_proj_dir, 'reports')
        report_dir1 = \
            os.path.join(self.test_proj_dir, common_report_dir, 'report_dir1')
        report_dir2 = \
            os.path.join(self.test_proj_dir, common_report_dir, 'report_dir2')

        cfg['reportdir'] = report_dir1
        cfg['checkers'] = [
            '-d', 'core.DivideZero', '-e', 'deadcode.DeadStores']
        codechecker.analyze(cfg, self.test_proj_dir)

        cfg['reportdir'] = report_dir2
        cfg['checkers'] = [
            '-e', 'core.DivideZero', '-d', 'deadcode.DeadStores']
        codechecker.analyze(cfg, self.test_proj_dir)

        def store_multiple_report_dirs(report_dirs):
            """ """
            run_name = "multiple_report_dirs"
            store_cmd = [
                env.codechecker_cmd(), "store",
                *report_dirs,
                "--name", run_name,
                "--url", env.parts_to_url(self.codechecker_cfg)]

            proc = subprocess.Popen(
                store_cmd, encoding="utf-8", errors="ignore",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _, err = proc.communicate()

            self.assertNotIn("UserWarning: Duplicate name", err)

            # Check the reports.
            query_cmd = [
                env.codechecker_cmd(), "cmd", "results",
                run_name,
                "--url", env.parts_to_url(self.codechecker_cfg),
                "-o", "json"]

            out = subprocess.check_output(
                query_cmd, encoding="utf-8", errors="ignore")
            reports = json.loads(out)

            self.assertTrue(
                any(r['checkerId'] == 'core.DivideZero' for r in reports))

            self.assertTrue(
                any(r['checkerId'] == 'deadcode.DeadStores' for r in reports))

            # Check the reports.
            rm_cmd = [
                env.codechecker_cmd(), "cmd", "del",
                "-n", run_name,
                "--url", env.parts_to_url(self.codechecker_cfg)]

            out = subprocess.check_output(
                rm_cmd, encoding="utf-8", errors="ignore")

        # Store report directories separately.
        store_multiple_report_dirs([report_dir1, report_dir2])

        # Store report directories recursively.
        store_multiple_report_dirs([common_report_dir])

        shutil.rmtree(common_report_dir)
