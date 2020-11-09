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

from libtest import env
from libtest import plist_test

from codechecker_common import util


class TestStore(unittest.TestCase):
    """Test storage reports"""

    def setUp(self):

        # Get the test workspace used to cppcheck tests.
        self._test_workspace = os.environ["TEST_WORKSPACE"]

        test_class = self.__class__.__name__
        print("Running " + test_class + " tests in " + self._test_workspace)

        self._test_cfg = env.import_test_cfg(self._test_workspace)

    def test_tim_path_prefix_store(self):
        """Trim the path prefix from the sored reports.

        The source file paths are converted to absolute with the
        temporary test directory, the test trims that temporary
        test directory from the source file path during the storage.
        """

        test_dir = os.path.dirname(os.path.realpath(__file__))

        report_dir = os.path.join(test_dir, "test_proj")

        codechecker_cfg = self._test_cfg["codechecker_cfg"]

        # Copy report files to a temporary directory not to modify the
        # files in the repository.
        # Report files will be overwritten during the tests.
        temp_workspace = os.path.join(
            codechecker_cfg["workspace"], "test_proj"
        )
        shutil.copytree(report_dir, temp_workspace)

        report_file = os.path.join(temp_workspace, "divide_zero.plist")

        # Convert file paths to absolute in the report.
        plist_test.prefix_file_path(report_file, temp_workspace)

        report_content = {}
        with open(report_file, mode="rb") as rf:
            report_content = plistlib.load(rf)

        trimmed_paths = [
            util.trim_path_prefixes(path, [temp_workspace])
            for path in report_content["files"]
        ]

        run_name = "store_test"
        store_cmd = [
            env.codechecker_cmd(),
            "store",
            temp_workspace,
            "--name",
            run_name,
            "--url",
            env.parts_to_url(codechecker_cfg),
            "--trim-path-prefix",
            temp_workspace,
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
            env.parts_to_url(codechecker_cfg),
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
