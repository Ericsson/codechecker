#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test reindex functionality.
"""

import os
import shutil
import subprocess
import unittest

from libtest import env
from codechecker_analyzer.cachedb import CacheDB


class TestReindex(unittest.TestCase):
    _ccClient = None

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('reindex')

        report_dir = os.path.join(TEST_WORKSPACE, 'reports')
        os.makedirs(report_dir)

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    def teardown_class(self):
        """Delete the workspace associated with this test"""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def setup_method(self, _):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._tu_collector_cmd = env.tu_collector_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')

    def __run_cmd(self, cmd, cwd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        print(out)
        print(err)
        self.assertEqual(process.returncode, 0)

    def test_reindex(self):
        build_json = os.path.join(self.test_workspace, "build.json")

        # Create and run log command
        log_cmd = [self._codechecker_cmd, "log", "-b", "gcc a.c",
                   "-o", build_json]
        self.__run_cmd(log_cmd, self.test_dir)

        # Create and run analyze command
        analyze_cmd = [
            self._codechecker_cmd, "analyze", "-c", build_json,
            "--analyzers", "clangsa", "-o", self.report_dir]
        self.__run_cmd(analyze_cmd, self.test_dir)

        plist_files_in_report_dir = [
            os.path.join(self.report_dir, f)
            for f in os.listdir(self.report_dir)
            if os.path.splitext(f)[1] == ".plist"]

        # Check if there are plist files in report_dir
        self.assertGreaterEqual(len(plist_files_in_report_dir), 1)

        a_c_clangsa_plist = None
        for f in plist_files_in_report_dir:
            if "a.c_clangsa" in f.split("/")[-1]:
                a_c_clangsa_plist = f
                break

        # Check if a.c_clangsa plist was found
        self.assertIsNotNone(a_c_clangsa_plist)

        # Create and run reindex command
        reindex_cmd = [
            self._codechecker_cmd, "reindex", "-f", self.report_dir]
        self.__run_cmd(reindex_cmd, self.test_dir)

        # Check if CacheDB was created
        self.assertTrue(os.path.isfile(
            os.path.join(self.report_dir, "cache.sqlite")))

        # Load CacheDB
        cachedb = CacheDB(self.report_dir)

        # Check if a.c_clangsa plist was indexed by the reindex command
        self.assertIn(a_c_clangsa_plist, cachedb.get_indexed_plist_files())

        source_files_in_test_dir = [
            os.path.join(self.test_dir, f)
            for f in os.listdir(self.test_dir)
            if os.path.splitext(f)[1] in [".c", ".h"]]

        # Check if source files were mapped to a.c_clangsa plist
        for f in source_files_in_test_dir:
            self.assertIn(a_c_clangsa_plist, cachedb.plist_query([f]))
