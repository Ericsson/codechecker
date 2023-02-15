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

import html
import json
import os
import shlex
import shutil
import inspect
import plistlib
import shutil
import subprocess
import unittest

from codechecker_report_converter import util

from codechecker_api.codeCheckerDBAccess_v6.ttypes import AnalysisInfoFilter
from libtest import codechecker
from libtest import env
from libtest import plist_test


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

    def setup_class(self):
        """Setup the environment for the tests then start the server."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('store_test')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        # Configuration options.
        codechecker_cfg = {
            'check_env': env.test_env(TEST_WORKSPACE),
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
            'test_project': 'store_test',
            'test_project_2': 'store_limited_product'
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()

        server_access['viewer_product'] = 'store_limited_product'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE,
                                             report_limit=2)

        server_access['viewer_product'] = 'store_test'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE,
                            {'codechecker_cfg': codechecker_cfg})

        # Copy test files to a temporary directory not to modify the
        # files in the repository.
        # Report files will be overwritten during the tests.
        test_dir = os.path.dirname(os.path.realpath(__file__))
        dst_dir = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(os.path.join(test_dir, "test_proj"), dst_dir)

        prefix_file_paths = [
            os.path.join(dst_dir, "divide_zero", "divide_zero.plist"),
            os.path.join(dst_dir, "double_suppress", "double_suppress.plist")]

        for file_name in prefix_file_paths:
            plist_test.prefix_file_path(file_name, os.path.dirname(file_name))

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        codechecker.remove_test_package_product(
            TEST_WORKSPACE,
            check_env,
            product="store_limited_product")

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):
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

        self._divide_zero_workspace = os.path.join(
            self._temp_workspace, "divide_zero")
        self._double_suppress_workspace = os.path.join(
            self._temp_workspace, "double_suppress")
        self._same_headers_workspace = os.path.join(
            self._temp_workspace, "same_headers")

        self.product_name = self._codechecker_cfg['viewer_product']

        self.limited_product_name = self._codechecker_cfg['test_project_2']

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        self._pr_client = env.setup_product_client(
            self._test_workspace, product=self.product_name)

        self._limited_pr_client = env.setup_product_client(
            self._test_workspace, product=self.limited_product_name)

        self.assertIsNotNone(self._pr_client)
        self.assertIsNotNone(self._limited_pr_client)

    def test_product_details(self):
        """
        Test that product details columns are set properly on run
        storage / removal events.
        """
        product = self._pr_client.getCurrentProduct()
        self.assertFalse(product.runCount)
        self.assertFalse(product.latestStoreToProduct)

        run_name = "product_details_test"
        store_cmd = [
            env.codechecker_cmd(), "store", self._divide_zero_workspace,
            "--name", run_name,
            "--url", env.parts_to_url(self._codechecker_cfg)]

        _call_cmd(store_cmd)

        product = self._pr_client.getCurrentProduct()
        self.assertTrue(product.runCount)
        self.assertTrue(product.latestStoreToProduct)

        rm_cmd = [
            env.codechecker_cmd(), "cmd", "del",
            "-n", run_name,
            "--url", env.parts_to_url(self._codechecker_cfg)]

        _call_cmd(rm_cmd)

        product = self._pr_client.getCurrentProduct()
        self.assertFalse(product.runCount)
        self.assertTrue(product.latestStoreToProduct)

    def test_trim_path_prefix_store(self):
        """Trim the path prefix from the sored reports.

        The source file paths are converted to absolute with the
        temporary test directory, the test trims that temporary
        test directory from the source file path during the storage.
        """
        report_file = os.path.join(
            self._divide_zero_workspace, "divide_zero.plist")

        report_content = {}
        with open(report_file, mode="rb") as rf:
            report_content = plistlib.load(rf)

        trimmed_paths = [
            util.trim_path_prefixes(path, [self._divide_zero_workspace])
            for path in report_content["files"]
        ]

        run_name = "store_test"
        store_cmd = [
            env.codechecker_cmd(), "store",
            self._divide_zero_workspace,
            "--name", run_name,
            "--url", env.parts_to_url(self._codechecker_cfg),
            "--trim-path-prefix", self._divide_zero_workspace,
            "--verbose", "debug",
        ]

        ret, out, err = _call_cmd(store_cmd)
        print(out)
        print(err)
        self.assertEqual(ret, 0, "Plist file could not store.")

        query_cmd = [
            env.codechecker_cmd(), "cmd", "results",
            run_name,
            # Use the 'Default' product.
            "--url", env.parts_to_url(self._codechecker_cfg),
            "-o", "json",
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
        codechecker.log(cfg, self._divide_zero_workspace)

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
        codechecker.analyze(cfg, self._divide_zero_workspace)

        with open(os.path.join(report_dir1, 'metadata.json'), 'r+',
                  encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
            data["tools"][0]["command"].append("<img />")

            f.seek(0)
            f.truncate()
            json.dump(data, f)

        cfg['reportdir'] = report_dir2
        cfg['checkers'] = [
            '-e', 'core.DivideZero', '-d', 'deadcode.DeadStores']
        codechecker.analyze(cfg, self._divide_zero_workspace)

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

            self.assertTrue(all(
                '<' not in i.analyzerCommand for i in analysis_info))
            self.assertTrue(any(
                html.escape('<') in i.analyzerCommand for i in analysis_info))

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

    def test_suppress_duplicated(self):
        """
        Test server if recognise duplicated suppress comments in the stored
        source code.
        """
        test_plist_file = "double_suppress.plist"

        store_cmd = [env.codechecker_cmd(), "store", "--url",
                     env.parts_to_url(self._codechecker_cfg), "--name",
                     "never",  "--input-format", "plist",
                     "--verbose", "debug", test_plist_file]

        ret, _, _ = _call_cmd(store_cmd, self._double_suppress_workspace)
        self.assertEqual(ret, 1, "Duplicated suppress comments was not "
                         "recognised.")

    def test_same_headers(self):
        """
        Same headers in different folders.

        On server side "path hash" prevents multiple storage of a report in a
        header when the header is included in multiple translation units.
        Otherwise a report would be stored as many times as many TU contains
        it. Earlier this "path hash" contained only the header file's name, so
        the reports of another header with the same name but different
        directory weren't stored.
        """
        def create_build_json(source_file):
            build_json = \
                os.path.join(self._same_headers_workspace, 'build.json')
            with open(build_json, 'w') as f:
                json.dump([{
                    'directory': '.',
                    'command': f'g++ -c {source_file}',
                    'file': source_file}], f)

        def analyze_tidy(cfg):
            build_json = os.path.join(cfg['workspace'], 'build.json')
            analyze_cmd = [env.codechecker_cmd(), "analyze", build_json,
                           "--analyzers", "clang-tidy", "-o",
                           cfg['reportdir']]
            _call_cmd(analyze_cmd, cfg['workspace'])

        cfg = dict(self._codechecker_cfg)
        cfg['workspace'] = self._same_headers_workspace
        cfg['reportdir'] = \
            os.path.join(self._same_headers_workspace, 'reports')

        store_cmd = [
            env.codechecker_cmd(), "store",
            "--url", env.parts_to_url(self._codechecker_cfg),
            "--name", "same_headers", cfg['reportdir']]
        query_cmd = [
            env.codechecker_cmd(), "cmd", "results",
            "same_headers",
            "--checker-name", "bugprone-sizeof-expression",
            "--url", env.parts_to_url(self._codechecker_cfg),
            "-o", "json"]

        create_build_json('same_headers1.cpp')
        analyze_tidy(cfg)

        _call_cmd(store_cmd, self._same_headers_workspace)

        out = subprocess.check_output(
            query_cmd, encoding="utf-8", errors="ignore")
        reports = json.loads(out)

        self.assertEqual(len(reports), 1)

        create_build_json('same_headers2.cpp')
        analyze_tidy(cfg)

        _call_cmd(store_cmd, self._same_headers_workspace)

        out = subprocess.check_output(
            query_cmd, encoding="utf-8", errors="ignore")
        reports = json.loads(out)

        self.assertEqual(len(reports), 2)

        create_build_json('same_headers3.cpp')
        analyze_tidy(cfg)

        _call_cmd(store_cmd, self._same_headers_workspace)

        out = subprocess.check_output(
            query_cmd, encoding="utf-8", errors="ignore")
        reports = json.loads(out)

        self.assertEqual(len(reports), 2)

    def test_store_limit(self):
        """
        Test store limit of a product.
        """

        run_name = "limit_test"
        store_cmd = [
            env.codechecker_cmd(), "store",
            self._divide_zero_workspace,
            "--name", run_name,
            "--url", env.parts_to_url(self._codechecker_cfg, 'test_project_2'),
            "--trim-path-prefix", self._divide_zero_workspace,
            "--verbose", "debug",
        ]

        _, out, _ = _call_cmd(store_cmd)
        self.assertIn("Report Limit Exceeded", out)
