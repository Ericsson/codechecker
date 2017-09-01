#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Diff feature tests. Comparing results from two runs.
"""
import os
import unittest
import logging

import re
import shared
import subprocess

from codeCheckerDBAccess.ttypes import DiffType
from codeCheckerDBAccess.ttypes import CompareData
from codeCheckerDBAccess.ttypes import ReportFilter_v2

from libtest.thrift_client_to_db import get_all_run_results_v2
from libtest.debug_printer import print_run_results
from libtest import env


def get_severity_level(name):
    """
    Convert severity level from the name to value.
    """
    return shared.ttypes.Severity._NAMES_TO_VALUES[name]


class Diff(unittest.TestCase):
    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        self._testproject_data = env.setup_test_proj_cfg(test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(test_workspace)

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]
        for r in test_runs:
            print(r)

        # There should be at least two runs for this test.
        self.assertIsNotNone(runs)
        self.assertNotEqual(len(runs), 0)
        self.assertGreaterEqual(len(runs), 2)

        # Name order matters from __init__ !
        self._base_runid = test_runs[0].runId  # base
        self._new_runid = test_runs[1].runId  # new

        self._codechecker_cmd = env.codechecker_cmd()
        self._report_dir = os.path.join(test_workspace, "reports")
        self._test_config = env.import_test_cfg(test_workspace)
        self._run_names = env.get_run_names(test_workspace)

    def test_get_diff_res_count_new(self):
        """
        Count the new results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)

        diff_res = self._cc_client.getRunResultCount_v2([base_run_id],
                                                        None,
                                                        cmp_data)
        # 5 new core.CallAndMessage issues.
        self.assertEqual(diff_res, 5)

    def test_get_diff_res_count_new_no_base(self):
        """
        Count the new results with no filter and no baseline
        run ids.
        """
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)

        diff_res = self._cc_client.getRunResultCount_v2([],
                                                        None,
                                                        cmp_data)
        # 5 new core.CallAndMessage issues.
        self.assertEqual(diff_res, 5)

    def test_get_diff_results_new(self):
        """
        Get the new results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)

        diff_res = self._cc_client.getRunResults_v2([base_run_id],
                                                    500,
                                                    0,
                                                    [],
                                                    None,
                                                    cmp_data)
        # 5 new core.CallAndMessage issues.
        self.assertEqual(len(diff_res), 5)

    def test_get_diff_results_resolved(self):
        """
        Get the resolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.RESOLVED)

        diff_res = self._cc_client.getRunResults_v2([base_run_id],
                                                    500,
                                                    0,
                                                    [],
                                                    None,
                                                    cmp_data)
        self.assertEqual(len(diff_res), 3)

    def test_get_diff_results_unresolved(self):
        """
        Get the unresolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        diff_res = self._cc_client.getRunResults_v2([base_run_id],
                                                    500,
                                                    0,
                                                    [],
                                                    None,
                                                    cmp_data)
        self.assertEqual(len(diff_res), 18)

    def test_get_diff_res_count_resolved(self):
        """
        Count the resolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.RESOLVED)

        diff_res = self._cc_client.getRunResultCount_v2([base_run_id],
                                                        None,
                                                        cmp_data)
        # 3 disappeared core.StackAddressEscape issues.
        self.assertEqual(diff_res, 3)

    def test_get_diff_res_count_unresolved(self):
        """
        Count the unresolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        base_count = self._cc_client.getRunResultCount_v2([base_run_id],
                                                          None,
                                                          None)
        logging.debug("Base run id: %d", base_run_id)
        logging.debug("Base count: %d", base_count)

        base_run_res = get_all_run_results_v2(self._cc_client, base_run_id)

        print_run_results(base_run_res)

        new_count = self._cc_client.getRunResultCount_v2([new_run_id],
                                                         None,
                                                         None)
        logging.debug("New run id: %d", new_run_id)
        logging.debug("New count: %d", new_count)

        new_run_res = get_all_run_results_v2(self._cc_client, new_run_id)

        print_run_results(new_run_res)

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        diff_res = self._cc_client.getRunResultCount_v2([base_run_id],
                                                        None,
                                                        cmp_data)

        self.assertEqual(diff_res, 18)

    def test_get_diff_res_count_unresolved_filter(self):
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        filter_severity_levels = [{"MEDIUM": 1}, {"LOW": 5},
                                  {"HIGH": 12}, {"STYLE": 0},
                                  {"UNSPECIFIED": 0}, {"CRITICAL": 0}]

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        for level in filter_severity_levels:
            for severity_level, test_result_count in level.items():
                sev = get_severity_level(severity_level)
                sev_filter = ReportFilter_v2(severity=[sev])

                diff_result_count = self._cc_client.getRunResultCount_v2(
                    [base_run_id], sev_filter, cmp_data)

                self.assertEqual(test_result_count, diff_result_count)

    def test_get_diff_checker_counts(self):
        """
        Test diff result types for new results.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)

        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    None,
                                                    cmp_data)

        # core.CallAndMessage is the new checker.
        test_res = {"core.CallAndMessage": 5}
        self.assertDictEqual(diff_res, test_res)

    def test_get_diff_checker_counts_core_new(self):
        """
        Test diff result types for new core checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)
        report_filter = ReportFilter_v2(checkerName=["*core*"])
        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    report_filter,
                                                    cmp_data)
        # core.CallAndMessage is the new checker.
        test_res = {"core.CallAndMessage": 5}
        self.assertDictEqual(diff_res, test_res)

    def test_get_diff_checker_counts_unix_resolved(self):
        """
        Test diff result types for resolved unix checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        report_filter = ReportFilter_v2(checkerName=["*core*"])
        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.RESOLVED)
        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    report_filter,
                                                    cmp_data)
        # Resolved core checkers.
        test_res = {'core.StackAddressEscape': 3}
        self.assertDictEqual(diff_res, test_res)

    def test_get_diff_checker_counts_core_unresolved(self):
        """
        Test diff result types for resolved unix checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        report_filter = ReportFilter_v2(checkerName=["*core*"])
        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)
        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    report_filter,
                                                    cmp_data)
        # Unesolved core checkers.
        test_res = {'core.NullDereference': 4, 'core.DivideZero': 3}
        self.assertDictContainsSubset(test_res, diff_res)

    def test_get_diff_checker_counts_all_unresolved(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    None,
                                                    cmp_data)
        # All unresolved checkers.
        test_res = {'core.DivideZero': 3,
                    'core.NullDereference': 4,
                    'cplusplus.NewDelete': 5,
                    'deadcode.DeadStores': 5,
                    'unix.Malloc': 1}

        self.assertDictContainsSubset(diff_res, test_res)

    def test_get_diff_severity_counts_all_unresolved(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        sev_res = self._cc_client.getSeverityCounts([base_run_id],
                                                    None,
                                                    cmp_data)
        test_res = {shared.ttypes.Severity.HIGH: 12,
                    shared.ttypes.Severity.LOW: 5,
                    shared.ttypes.Severity.MEDIUM: 1}
        self.assertDictEqual(sev_res, test_res)

    def test_get_diff_severity_counts_all_new(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)

        sev_res = self._cc_client.getSeverityCounts([base_run_id],
                                                    None,
                                                    cmp_data)
        test_res = {shared.ttypes.Severity.HIGH: 5}
        self.assertDictEqual(sev_res, test_res)

    def test_get_diff_new_review_status_counts(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.NEW)

        res = self._cc_client.getReviewStatusCounts([base_run_id],
                                                    None,
                                                    cmp_data)

        test_res = {shared.ttypes.ReviewStatus.UNREVIEWED: 5}
        self.assertDictEqual(res, test_res)

    def test_get_diff_unres_review_status_counts(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        res = self._cc_client.getReviewStatusCounts([base_run_id],
                                                    None,
                                                    cmp_data)

        test_res = {shared.ttypes.ReviewStatus.UNREVIEWED: 18}
        self.assertDictEqual(res, test_res)

    def test_get_diff_res_review_status_counts(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.RESOLVED)

        res = self._cc_client.getReviewStatusCounts([base_run_id],
                                                    None,
                                                    cmp_data)

        test_res = {shared.ttypes.ReviewStatus.UNREVIEWED: 3}
        self.assertDictEqual(res, test_res)

    def test_get_diff_res_types_resolved(self):
        """
        Test diff result types for resolved results.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.RESOLVED)

        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    None,
                                                    cmp_data)
        test_res = {'core.StackAddressEscape': 3}
        self.assertDictEqual(diff_res, test_res)

    def test_get_diff_res_types_unresolved(self):
        """
        Test diff result types for unresolved results with no filter
        on the api.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res_types_filter = self._testproject_data[self._clang_to_test][
            'diff_res_types_filter']

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        diff_res = \
            self._cc_client.getCheckerCounts([base_run_id],
                                             None,
                                             cmp_data)

        test_res = {'cplusplus.NewDelete': 5,
                    'deadcode.DeadStores': 5,
                    'unix.Malloc': 1,
                    'core.NullDereference': 4,
                    'core.DivideZero': 3}
        self.assertDictEqual(diff_res, test_res)

    def test_get_diff_res_types_unresolved_filter(self):
        """
        Test diff result types for unresolved results with filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res_types_filter = self._testproject_data[self._clang_to_test][
            'diff_res_types_filter']

        cmp_data = CompareData(run_ids=[new_run_id],
                               diff_type=DiffType.UNRESOLVED)

        for level in diff_res_types_filter:
            for checker_name, test_result_count in level.items():
                checker_filter = ReportFilter_v2(checkerName=[checker_name])
                diff_res = \
                    self._cc_client.getCheckerCounts([base_run_id],
                                                     checker_filter,
                                                     cmp_data)

                # There should be only one result for each checker name.
                self.assertEqual(test_result_count, diff_res[checker_name])

    def test_local_compare_res_count_new(self):
        """
        Count the new results with no filter in local compare mode.
        """
        base_run_name = self._run_names[0]
        vh = self._test_config['codechecker_cfg']['viewer_host']
        vp = self._test_config['codechecker_cfg']['viewer_port']
        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--new",
                    "--host", vh,
                    "--port", str(vp),
                    "-b", base_run_name,
                    "-n", self._report_dir
                    ]
        print(diff_cmd)
        process = subprocess.Popen(
            diff_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=os.environ['TEST_WORKSPACE'])
        out, err = process.communicate()
        print(out+err)

        # 5 new core.CallAndMessage issues.
        count = len(re.findall(r'\[core\.CallAndMessage\]', out))
        self.assertEqual(count, 5)

    def test_local_compare_res_count_resovled(self):
        """
        Count the resolved results with no filter in local compare mode.
        """
        base_run_name = self._run_names[0]
        vh = self._test_config['codechecker_cfg']['viewer_host']
        vp = self._test_config['codechecker_cfg']['viewer_port']
        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--resolved",
                    "--host", vh,
                    "--port", str(vp),
                    "-b", base_run_name,
                    "-n", self._report_dir
                    ]
        print(diff_cmd)
        process = subprocess.Popen(
            diff_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=os.environ['TEST_WORKSPACE'])
        out, err = process.communicate()
        print(out+err)

        # # 3 disappeared core.StackAddressEscape issues
        count = len(re.findall(r'\[core\.StackAddressEscape\]', out))
        self.assertEqual(count, 3)

    def test_local_compare_res_count_unresovled(self):
        """
        Count the unresolved results with no filter in local compare mode.
        """
        base_run_name = self._run_names[0]
        vh = self._test_config['codechecker_cfg']['viewer_host']
        vp = self._test_config['codechecker_cfg']['viewer_port']
        diff_cmd = [self._codechecker_cmd, "cmd", "diff",
                    "--unresolved",
                    "--host", vh,
                    "--port", str(vp),
                    "-b", base_run_name,
                    "-n", self._report_dir
                    ]
        print(diff_cmd)
        process = subprocess.Popen(
            diff_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=os.environ['TEST_WORKSPACE'])
        out, err = process.communicate()
        print(out+err)

        # # 3 disappeared core.StackAddressEscape issues
        count = len(re.findall(r'\[core\.DivideZero\]', out))
        self.assertEqual(count, 3)
        count = len(re.findall(r'\[deadcode\.DeadStores\]', out))
        self.assertEqual(count, 5)
        count = len(re.findall(r'\[core\.NullDereference\]', out))
        self.assertEqual(count, 4)
        count = len(re.findall(r'\[cplusplus\.NewDelete\]', out))
        self.assertEqual(count, 5)
        count = len(re.findall(r'\[unix\.Malloc\]', out))
        self.assertEqual(count, 1)
        count = len(re.findall(r'\[core.DivideZero\]', out))
        self.assertEqual(count, 3)
