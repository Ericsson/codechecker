#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test command line diffing (as opposed to natively using API calls).
"""


import os
import shutil
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import \
        ReviewStatus, DiffType, ReportFilter, DetectionStatus

from codechecker_client.cmd_line_client import \
    get_diff_local_dirs, get_diff_remote_run_local_dir, \
    get_diff_local_dir_remote_run, get_diff_remote_runs, init_logger

from libtest import codechecker, env
from libtest.thrift_client_to_db import get_all_run_results


class TestDiffFromCmdLine(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing review_status."""

        workspace_name = 'diff_cmdline'
        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace(workspace_name)

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'suppress_file': None,
            'skip_list_file': None,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'analyzers': ['clangsa']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = workspace_name
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        test_config = {}
        test_config['codechecker_cfg'] = codechecker_cfg

        env.export_test_cfg(TEST_WORKSPACE, test_config)

        init_logger(None, None)

    def teardown_class(self):
        """Clean up after the test."""

        # TODO: If environment variable is set keep the workspace
        # and print out the path.
        global TEST_WORKSPACE

        check_env = env.import_test_cfg(TEST_WORKSPACE)[
            'codechecker_cfg']['check_env']
        codechecker.remove_test_package_product(TEST_WORKSPACE, check_env)

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE, ignore_errors=True)

    def setup_method(self, method):
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

    def teardown_method(self, method):
        """ Remove all review status rules after each test cases. """
        self.__remove_all_runs()
        self.__remove_all_rules()

        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")
        shutil.rmtree(dir1, ignore_errors=True)
        shutil.rmtree(dir2, ignore_errors=True)

    # ===-----------------------------------------------------------------=== #

    def __remove_all_runs(self):
        for run_data in self._cc_client.getRunData(None, None, 0, None):
            ret = self._cc_client.removeRun(run_data.runId, None)
            self.assertTrue(ret)
            print(f"Successfully removed run '{run_data.name}'.")

    def __remove_all_rules(self):
        """ Removes all review status rules from the database. """
        self._cc_client.removeReviewStatusRules(None)

        # Check that there is no review status rule in the database.
        self.assertFalse(self._cc_client.getReviewStatusRulesCount(None))

        rules = self._cc_client.getReviewStatusRules(None, None, None, 0)
        self.assertFalse(rules)

    def __analyze(self, file_dir, source_code):
        build_json_path = os.path.join(file_dir, "build.json")

        build_json = f"""
[{{
    "directory": "{file_dir}",
    "file": "main.c",
    "command": "gcc main.c -o /dev/null"
}}]
"""
        os.makedirs(file_dir, exist_ok=True)

        with open(os.path.join(file_dir, "main.c"), "w") as f:
            f.write(source_code)

        with open(build_json_path, "w") as f:
            f.write(build_json)

        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg["workspace"] = file_dir
        codechecker_cfg["reportdir"] = os.path.join(file_dir, "reports")
        codechecker_cfg['analyzers'] = ['clangsa', 'clang-tidy']

        codechecker.analyze(codechecker_cfg, file_dir)

    def __store(self, file_dir, store_name, tag=None):
        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg["workspace"] = file_dir
        codechecker_cfg["reportdir"] = \
            os.path.join(file_dir, "reports")
        codechecker_cfg["tag"] = tag
        codechecker.store(codechecker_cfg, store_name)

    def __analyze_and_store(self, file_dir, store_name, source_code, tag=None):
        self.__analyze(file_dir, source_code)
        self.__store(file_dir, store_name, tag)

    def __get_run_id(self, run_name):
        runs = self._cc_client.getRunData(None, None, 0, None)
        self.assertEqual(len(runs), 1)
        test_run = [run for run in runs if run.name == run_name]
        self.assertEqual(len(test_run), 1)
        return test_run[0].runid

    # ===-----------------------------------------------------------------=== #
    # Local-local tests.
    # ===-----------------------------------------------------------------=== #

    def test_local_local_different(self):
        # Diff two different, local runs.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""

        src_nullptr_deref = """
void b() {
  int *i = 0;
  *i = 5;
}
"""
        self.__analyze(dir1, src_div_by_zero)
        self.__analyze(dir2, src_nullptr_deref)

        report_filter = ReportFilter()
        report_filter.reviewStatus = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir1], [], [dir2], [])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)

        # a() is the old report.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)

        # There are no common reports.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir2], [], [dir1], [])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 1)

        # a() is the old report.
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 1)

        # There are no common reports.
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_local_local_identical(self):
        # Diff two identical, local runs.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze(dir1, src_div_by_zero)
        self.__analyze(dir2, src_div_by_zero)

        report_filter = ReportFilter()
        report_filter.reviewStatus = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir1], [], [dir2], [])
            return len(reports)

        # No new reports appeared.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)

        # No reports disappeared.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)

        # There is a single report that has remained.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 1)

    def test_localFPAnnotated_local_identical(self):
        # Diff identical, local runs, where the baseline report is suppressed
        # via //codechecker_suppress.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero_FP = """
void a() {
  int i = 0;
  // codechecker_false_positive [all] SUPPRESS ALL
  (void)(10 / i);
}
"""
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze(dir1, src_div_by_zero_FP)
        self.__analyze(dir2, src_div_by_zero)

        def get_run_diff_count(diff_type: DiffType):
            report_filter = ReportFilter()
            report_filter.reviewStatus = []

            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir1], [], [dir2], [])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            report_filter = ReportFilter()
            report_filter.reviewStatus = []

            reports, _ = get_diff_local_dirs(
                    report_filter, diff_type, [dir2], [], [dir1], [])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    # ===-----------------------------------------------------------------=== #
    # Local-Remote tests.
    # ===-----------------------------------------------------------------=== #

    def test_local_remote_different(self):
        # Create two non-identical runs, store one on the server, leave one
        # locally.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""

        src_nullptr_deref = """
void b() {
  int *i = 0;
  *i = 5;
}
"""
        self.__analyze_and_store(dir1, "run1", src_div_by_zero)
        self.__analyze(dir2, src_nullptr_deref)

        report_filter = ReportFilter()
        report_filter.reviewStatus = []

        def get_run_diff_count(diff_type: DiffType):
            # Observe that the remote run is the baseline, and the local run
            # is new.
            reports, _, _ = get_diff_remote_run_local_dir(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1"], [dir2], [])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)

        # a() is the old report.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)

        # There are no common reports.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            # Note how this isn't the same function!!
            reports, _, _ = get_diff_local_dir_remote_run(
                    self._cc_client, report_filter, diff_type, [],
                    [dir2], [], ["run1"])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 1)

        # a() is the old report.
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 1)

        # There are no common reports.
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_local_remote_identical(self):
        # Create two identical runs, store one on the server, leave one
        # locally.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze_and_store(dir1, "run1", src_div_by_zero)
        self.__analyze(dir2, src_div_by_zero)

        report_filter = ReportFilter()
        report_filter.reviewStatus = []

        def get_run_diff_count(diff_type: DiffType):
            # Observe that the remote run is the baseline, and the local run
            # is new.
            reports, _, _ = get_diff_remote_run_local_dir(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1"], [dir2], [])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 1)

        def get_run_diff_count_reverse(diff_type: DiffType):
            # Note how this isn't the same function!!
            reports, _, _ = get_diff_local_dir_remote_run(
                    self._cc_client, report_filter, diff_type, [],
                    [dir2], [], ["run1"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 1)

    def test_localFPAnnotated_remote_identical(self):
        # Create two identical runs, store one on the server, leave one
        # locally.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero_FP = """
void a() {
  int i = 0;
  // codechecker_false_positive [all] SUPPRESS ALL
  (void)(10 / i);
}
"""
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze(dir1, src_div_by_zero_FP)
        self.__analyze_and_store(dir2, "run2", src_div_by_zero)

        report_filter = ReportFilter()
        report_filter.reviewStatus = []

        def get_run_diff_count(diff_type: DiffType):
            # Observe that the remote run is the baseline, and the local run
            # is new.
            reports, _, _ = get_diff_remote_run_local_dir(
                    self._cc_client, report_filter, diff_type, [],
                    ["run2"], [dir1], [])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)

        # a() is the old report.
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)

        # There are no common reports.
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            # Note how this isn't the same function!!
            reports, _, _ = get_diff_local_dir_remote_run(
                    self._cc_client, report_filter, diff_type, [],
                    [dir1], [], ["run2"])
            return len(reports)

        # b() is a new report.
        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 1)

        # a() is the old report.
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)

        # There are no common reports.
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_local_remoteFPAnnotated_identical(self):
        # Create two identical runs, store one on the server with a FP source
        # code suppression, leave one locally.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero_FP = """
void a() {
  int i = 0;
  // codechecker_false_positive [all] SUPPRESS ALL
  (void)(10 / i);
}
"""
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze(dir1, src_div_by_zero)
        self.__analyze_and_store(dir2, "run2", src_div_by_zero_FP)

        report_filter = ReportFilter()
        report_filter.reviewStatus = []

        def get_run_diff_count(diff_type: DiffType):
            # Observe that the remote run is the baseline, and the local run
            # is new.
            reports, _, _ = get_diff_remote_run_local_dir(
                    self._cc_client, report_filter, diff_type, [],
                    ["run2"], [dir1], [])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            # Note how this isn't the same function!!
            reports, _, _ = get_diff_local_dir_remote_run(
                    self._cc_client, report_filter, diff_type, [],
                    [dir1], [], ["run2"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_local_remoteReviewStatusRule_identical(self):
        """
        Even though the local report is not marked as a false positive, we
        expect the review status rule on the server to affect it.
        Note that the remote run is the baseline, which suggests that the
        review status rule is also a part of the baseline (it precedes the
        local run), yet the rule still affects the local run.
        This implies that review status rules are a timeless property -- once
        a hash has a rule, all reports matching it before or after the rule
        was made are affected.
        Since neither the report is not present in either of the baseline's,
        nor the new run's set outstanding reports, it shouldn't be present in
        any of the NEW, RESOLVED or UNRESOLVED sets.
        """
        # Create two identical runs, store one on the server, leave one
        # locally.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        self.__analyze_and_store(dir1, "run1", src_div_by_zero)

        # Add a "false positive" review status rule on the stored report.
        results = get_all_run_results(self._cc_client)
        self.assertEqual(len(results), 1)
        self._cc_client.addReviewStatusRule(
                results[0].bugHash, ReviewStatus.FALSE_POSITIVE, "")

        self.__analyze(dir2, src_div_by_zero)

        def get_run_diff_count(diff_type: DiffType):
            report_filter = ReportFilter()
            # Observe that the remote run is the baseline, and the local run
            # is new.
            report_filter.reviewStatus = []
            reports, _, _ = get_diff_remote_run_local_dir(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1"], [dir2], [])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            report_filter = ReportFilter()
            report_filter.reviewStatus = []
            # Note how this isn't the same function!!
            reports, _, _ = get_diff_local_dir_remote_run(
                    self._cc_client, report_filter, diff_type, [],
                    [dir2], [], ["run1"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    # TODO: source code suppression and review status rule conflict resolution
    # TODO: diff against a tag on the server, not just a run

    # ===-----------------------------------------------------------------=== #
    # Remote-Remote tests.
    # ===-----------------------------------------------------------------=== #

    # TODO: remote-remote diffs not concerning tags

    # ===--- Remote-Remote tests in between tags. ------------------------=== #

    # Ideally, diffing tags should work the same as diffing two remote runs or
    # local directory.

    def test_remoteTag_remoteTag_identical(self):
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        # Note that we're storing under the same run.
        self.__analyze_and_store(dir1, "run1", src_div_by_zero, "tag1")
        self.__analyze_and_store(dir2, "run1", src_div_by_zero, "tag2")

        report_filter = ReportFilter()
        report_filter.reviewStatus = []
        report_filter.detection_status = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag1"], ["run1:tag2"])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 1)

        def get_run_diff_count_reverse(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag2"], ["run1:tag1"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 1)

    def test_remoteTag_remoteTag_different(self):
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        src_nullptr_deref = """
void b() {
  int *i = 0;
  *i = 5;
}
"""
        # Note that we're storing under the same run.
        self.__analyze_and_store(dir1, "run1", src_div_by_zero, "tag1")
        self.__analyze_and_store(dir2, "run1", src_nullptr_deref, "tag2")

        report_filter = ReportFilter()
        report_filter.reviewStatus = []
        report_filter.detectionStatus = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag1"], ["run1:tag2"])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        # This is the default value for --review-status, but for tags, we
        # should ignore it.
        report_filter.detectionStatus = [DetectionStatus.NEW,
                                         DetectionStatus.REOPENED,
                                         DetectionStatus.UNRESOLVED]

        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag2"], ["run1:tag1"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_remoteTagFPAnnotated_remoteTag_identical(self):
        """
        Test source code suppression changes -- in tag1, a FP suppression is
        present, and in tag2, it disappears. Internally, as of writing, this
        will irreversibly remove the fixed_at attribute, so we are not really
        able to get this right.
        """
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero_FP = """
void a() {
  int i = 0;
  // codechecker_false_positive [all] SUPPRESS ALL
  (void)(10 / i);
}
"""
        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        # Note that we're storing under the same run.
        self.__analyze_and_store(dir1, "run1", src_div_by_zero_FP, "tag1")
        self.__analyze_and_store(dir2, "run1", src_div_by_zero, "tag2")

        report_filter = ReportFilter()
        report_filter.reviewStatus = []
        report_filter.detection_status = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag1"], ["run1:tag2"])
            return len(reports)

        # FIXME: The FP suppression disappeared from one tag to the next, so it
        # should be in the NEW set.
        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 1)

        def get_run_diff_count_reverse(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag2"], ["run1:tag1"])
            return len(reports)

        # FIXME: The FP suppression disappeared from one tag to the next, so it
        # should be in the RESOLVED set when the diff sets are reversed.
        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 1)

    def test_remoteTag_remoteTagFPAnnotated(self):
        """
        Test source code suppression changes -- in tag1, there is no
        suppression, and in tag2, there is an FP suppression. This should be
        doable, as first, the fixed_at attribute is NULL, then it'll be set --
        there is no permanent loss of information.
        """
        # Diff two different, local runs.
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        src_div_by_zero_FP = """
void a() {
  int i = 0;
  // codechecker_false_positive [all] SUPPRESS ALL
  (void)(10 / i);
}
"""
        # Note that we're storing under the same run.
        self.__analyze_and_store(dir1, "run1", src_div_by_zero, "tag1")
        self.__analyze_and_store(dir2, "run1", src_div_by_zero_FP, "tag2")

        report_filter = ReportFilter()
        report_filter.reviewStatus = []
        report_filter.detection_status = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag1"], ["run1:tag2"])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag2"], ["run1:tag1"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_remoteTagReviewStatusRule_remoteTag_identical(self):
        """
        You can find more context for why this is the expected result in the
        docs of test_local_remoteReviewStatusRule_identical.
        """
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_div_by_zero = """
void a() {
  int i = 0;
  (void)(10 / i);
}
"""
        # Note that we're storing under the same run.
        self.__analyze_and_store(dir1, "run1", src_div_by_zero, "tag1")

        # Add a "false positive" review status rule on the stored report.
        results = get_all_run_results(self._cc_client)
        self.assertEqual(len(results), 1)
        self._cc_client.addReviewStatusRule(
                results[0].bugHash, ReviewStatus.FALSE_POSITIVE, "")

        self.__analyze_and_store(dir2, "run1", src_div_by_zero, "tag2")

        report_filter = ReportFilter()
        report_filter.reviewStatus = []
        report_filter.detection_status = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag1"], ["run1:tag2"])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 0)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 1)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        def get_run_diff_count_reverse(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag2"], ["run1:tag1"])
            return len(reports)

        self.assertEqual(get_run_diff_count_reverse(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count_reverse(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count_reverse(DiffType.UNRESOLVED), 0)

    def test_remoteTag_remoteTag_FixedAtDate(self):
        """
        When a run disappears from one tag to the next, we regard it as fixed,
        and set it fixed_at date. Test whether just because the fixed_at date
        is set, we still regard it as an outstanding report if we diff it in
        a context where the bug still isn't fixed yet.

        You can read more about this bug here:
        https://github.com/Ericsson/codechecker/pull/3853
        """
        dir1 = os.path.join(self.test_workspace, "dir1")
        dir2 = os.path.join(self.test_workspace, "dir2")

        src_no_warnings = """
void a() {
  // No faults.
}
"""

        src_nullptr_deref = """
void b() {
  int *i = 0;
  *i = 5;
}
"""
        # Note that we're storing under the same run.
        self.__analyze_and_store(dir1, "run1", src_no_warnings, "tag1")
        self.__analyze_and_store(dir2, "run1", src_nullptr_deref, "tag2")

        report_filter = ReportFilter()
        report_filter.reviewStatus = []
        report_filter.detection_status = []

        def get_run_diff_count(diff_type: DiffType):
            reports, _, _ = get_diff_remote_runs(
                    self._cc_client, report_filter, diff_type, [],
                    ["run1:tag1"], ["run1:tag2"])
            return len(reports)

        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)

        # NOTE that we store the first report dir again. The report in tag2 is
        # abscent, so its fixed_at date will be set. Still, the diff in between
        # tag1 and tag2 shouldn't change.
        self.__analyze_and_store(dir1, "run1", src_no_warnings, "tag3")

        self.assertEqual(get_run_diff_count(DiffType.NEW), 1)
        self.assertEqual(get_run_diff_count(DiffType.RESOLVED), 0)
        self.assertEqual(get_run_diff_count(DiffType.UNRESOLVED), 0)
