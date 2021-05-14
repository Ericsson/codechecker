#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test a binary (pypi, snap) package.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class TestBinaryPackage(unittest.TestCase):
    """
    Binary package tests.
    """

    def setUp(self):
        self.codechecker_bin = os.environ.get("CODECHECKER_BIN", "CodeChecker")
        self.compiler_bin = os.environ.get("CC", "gcc")

        self.test_workspace = tempfile.mkdtemp()

        self.source_file_path = os.path.join(self.test_workspace, "main.cpp")
        with open(self.source_file_path, 'w',
                  encoding="utf-8", errors="ignore") as f:
            f.write("""
int main()
{
  int i = 1 / 0;
  sizeof(i);

  return 0;
}
""")

        self.old_pwd = os.getcwd()
        os.chdir(self.test_workspace)

    def tearDown(self):
        """ Restore environment and clear the workspace. """
        os.chdir(self.old_pwd)
        shutil.rmtree(self.test_workspace, True)

    def _log(self, build_cmd):
        fd, build_file_path = tempfile.mkstemp(
            suffix=".json", prefix="compilation_database_",
            dir=self.test_workspace)
        os.close(fd)

        if sys.platform in ['linux']:
            subprocess.call(
                [
                    self.codechecker_bin, "log",
                    "-b", build_cmd,
                    "-o", build_file_path
                ],
                cwd=self.test_workspace,
                encoding="utf-8",
                errors="ignore")
        else:
            build_log = [
                {
                    "directory": self.test_workspace,
                    "command": (f"{self.compiler_bin} -c "
                                 "{self.source_file_path}"),
                    "file": self.source_file_path
                }
            ]

            with open(build_file_path, 'w', encoding="utf-8",
                      errors="ignore") as f:
                json.dump(build_log, f)

        return build_file_path

    def test_log_analyze_parse(self):
        """ Test CodeChecker log, analyze and parse. """
        # Log the project.
        build_cmd = f"{self.compiler_bin} -c {self.source_file_path}"
        build_file_path = self._log(build_cmd)

        self.assertTrue(os.path.exists(build_file_path))
        with open(build_file_path, 'r',
                  encoding="utf-8", errors="ignore") as f:
            build_actions = json.load(f)
            self.assertEqual(len(build_actions), 1)

        # Analyze the project.
        report_dir = os.path.join(self.test_workspace, "report_dir")
        process = subprocess.Popen(
            [
                self.codechecker_bin, "analyze",
                build_file_path,
                "-o", report_dir
            ],
            encoding="utf-8",
            errors="ignore")
        process.communicate()
        self.assertEqual(process.returncode, 0)

        # Parse the results.
        process = subprocess.Popen(
            [
                self.codechecker_bin, "parse",
                report_dir,
                "-e", "json"
            ],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()
        self.assertEqual(process.returncode, 2)
        reports = json.loads(out)
        self.assertTrue(len(reports) > 0)
