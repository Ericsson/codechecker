#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""diff_remote function test.

Test the compraison of two remote (in the database) runs.
"""

import os
import re
import shutil
import sys
import unittest
import uuid
from datetime import datetime, timedelta

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CompareData, \
    DiffType, Order, ReportFilter, ReviewStatus, RunHistoryFilter, \
    RunSortMode, RunSortType, Severity

from codechecker_report_converter.report import InvalidFileContentMsg

from libtest import codechecker
from libtest import env
from libtest import project
from libtest.codechecker import get_diff_results
from libtest.debug_printer import print_run_results
from libtest.thrift_client_to_db import get_all_run_results


def get_severity_level(name):
    """
    Convert severity level from the name to value.
    """
    return Severity._NAMES_TO_VALUES[name]


def str_to_date(date_str):
    """ Converts the given string to date.

    If the given string and the format code passed to the strptime() doesn't
    match, it will throw a ValueError exception.
    """
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')


class DiffRemote(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing diff_remote."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('diff_remote')

        # Set the TEST_WORKSPACE used by the tests.
        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_config = {}

        test_project = 'cpp'

        project_info = project.get_info(test_project)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_base = os.path.join(TEST_WORKSPACE, "test_proj_base")
        shutil.copytree(project.path(test_project), test_proj_path_base)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_new = os.path.join(TEST_WORKSPACE, "test_proj_new")
        shutil.copytree(project.path(test_project), test_proj_path_new)

        # Copy the test project to the workspace. The tests should
        # work only on this test project.
        test_proj_path_update = \
            os.path.join(TEST_WORKSPACE, "test_proj_update")
        shutil.copytree(project.path(test_project), test_proj_path_update)

        project_info['project_path_base'] = test_proj_path_base
        project_info['project_path_new'] = test_proj_path_new
        project_info['project_path_update'] = test_proj_path_update

        # Suppress file should be set here if needed by the tests.
        suppress_file = None

        # Skip list file should be set here if needed by the tests.
        skip_list_file = None

        # Get an environment which should be used by the tests.
        test_env = env.test_env(TEST_WORKSPACE)

        # Create a basic CodeChecker config for the tests, this should
        # be imported by the tests and they should only depend on these
        # configuration options.
        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'trim_path_prefix': TEST_WORKSPACE,
            'analyzers': ['clangsa']
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'diff_remote'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # ===-------------------------------------------------------------=== #
        # Baseline analysis.
        # ===-------------------------------------------------------------=== #

        # ===-------------------------- Analysis -------------------------=== #
        altered_file = os.path.join(test_proj_path_base,
                                    "call_and_message.cpp")
        project.insert_suppression(altered_file)
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_base,
                                                    'reports')
        codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                       '-d', 'core.NullDereference']

        ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_base)
        if ret:
            sys.exit(1)
        print('Analyzing base was successful.')

        # Store base results.
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_base,
                                                    'reports')

        # ===------------------------- Store 1. --------------------------=== #
        test_project_name_base = project_info['name'] + '_' + uuid.uuid4().hex
        ret = codechecker.store(codechecker_cfg, test_project_name_base)
        if ret:
            sys.exit(1)

        # ===------------------------- Store 2. --------------------------=== #
        # Store with a literal ':' in the name.
        ret = codechecker.store(codechecker_cfg,
                                test_project_name_base + ":base")
        if ret:
            sys.exit(1)

        # ===-------------------------------------------------------------=== #
        # New analysis (as opposed to baseline, this is the newer version).
        # ===-------------------------------------------------------------=== #

        # ===-------------------------- Analysis -------------------------=== #
        altered_file = os.path.join(test_proj_path_new, "call_and_message.cpp")
        project.insert_suppression(altered_file)
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_new,
                                                    'reports')
        codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                       '-e', 'core.NullDereference']

        ret = codechecker.log_and_analyze(codechecker_cfg, test_proj_path_new)
        if ret:
            sys.exit(1)
        print('Analyzing new was successful.')

        # Store new results.
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_new,
                                                    'reports')

        # ===------------------------- Store 1. --------------------------=== #
        test_project_name_new = project_info['name'] + '_' + uuid.uuid4().hex
        ret = codechecker.store(codechecker_cfg, test_project_name_new)
        if ret:
            sys.exit(1)

        # ===------------------------- Store 2. --------------------------=== #
        # Store with a literal ':' in the name.
        ret = codechecker.store(codechecker_cfg,
                                test_project_name_new + ":new")
        if ret:
            sys.exit(1)

        # ===-------------------------------------------------------------=== #
        # Another round of analyses for tags -- tag1
        # ===-------------------------------------------------------------=== #

        # ===-------------------------- Analysis -------------------------=== #
        # Analyze multiple times to store results with multiple tags.
        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_update,
                                                    'reports')

        test_project_name_update = \
            project_info['name'] + '_' + uuid.uuid4().hex
        codechecker_cfg['checkers'] = ['-d', 'core.CallAndMessage',
                                       '-e', 'core.StackAddressEscape'
                                       ]

        codechecker_cfg['reportdir'] = os.path.join(test_proj_path_update,
                                                    'reports')

        ret = codechecker.log_and_analyze(codechecker_cfg,
                                          test_proj_path_update)
        if ret:
            sys.exit(1)

        # ===--------------------------- Store ---------------------------=== #
        # Store update with t1 tag.
        codechecker_cfg['tag'] = 't1'
        ret = codechecker.store(codechecker_cfg, test_project_name_update)
        if ret:
            sys.exit(1)

        # ===-------------------------------------------------------------=== #
        # Another round of analyses for tags -- tag2
        # ===-------------------------------------------------------------=== #

        # ===-------------------------- Analysis -------------------------=== #
        codechecker_cfg['checkers'] = ['-e', 'core.CallAndMessage',
                                       '-d', 'core.StackAddressEscape'
                                       ]
        ret = codechecker.analyze(codechecker_cfg, test_proj_path_update)
        if ret:
            sys.exit(1)

        # ===--------------------------- Store ---------------------------=== #
        # Store update with t2 tag.
        codechecker_cfg['tag'] = 't2'
        ret = codechecker.store(codechecker_cfg, test_project_name_update)
        if ret:
            sys.exit(1)

        # ===-------------------------------------------------------------=== #
        # Another round of analyses for tags -- tag3
        # Mind that the analysis config from tag2 to tag3 is unchanged.
        # ===-------------------------------------------------------------=== #

        # ===-------------------------- Analysis -------------------------=== #
        ret = codechecker.log_and_analyze(codechecker_cfg,
                                          test_proj_path_update)
        if ret:
            sys.exit(1)

        # ===--------------------------- Store ---------------------------=== #
        # Store update with t3 tag.
        codechecker_cfg['tag'] = 't3'
        ret = codechecker.store(codechecker_cfg, test_project_name_update)
        if ret:
            sys.exit(1)

        # ===-------------------------------------------------------------=== #
        # Done with the analyses and stores.
        # ===-------------------------------------------------------------=== #

        # Order of the test run names matter at comparison!
        codechecker_cfg['run_names'] = [test_project_name_base,
                                        test_project_name_new,
                                        test_project_name_update]

        test_config['test_project'] = project_info
        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
        env.export_test_cfg(TEST_WORKSPACE, test_config)

        # Remove report directories which are not used anymore.
        shutil.rmtree(test_proj_path_base, ignore_errors=True)
        shutil.rmtree(test_proj_path_new, ignore_errors=True)

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

    def setup_method(self, _):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the test configuration from the prepared int the test workspace.
        self.test_cfg = env.import_test_cfg(self.test_workspace)

        # Get the clang version which is tested.
        self._clang_to_test = env.clang_to_test()

        # Get the test project configuration from the prepared test workspace.
        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()

        # Get the run names which belong to this test.
        # Name order matters from __init__ !
        run_names = env.get_run_names(self.test_workspace)

        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        runs = self._cc_client.getRunData(None, None, 0, sort_mode)
        self._test_runs = [run for run in runs if run.name in run_names]

        # There should be at least two runs for this test.
        self.assertIsNotNone(runs)
        self.assertNotEqual(len(runs), 0)
        self.assertGreaterEqual(len(runs), 2)

        # Name order matters from __init__ !
        self._base_runid = self._test_runs[0].runId
        self._new_runid = self._test_runs[1].runId
        self._update_runid = self._test_runs[2].runId

        self._url = env.parts_to_url(self.test_cfg['codechecker_cfg'])

        self._env = self.test_cfg['codechecker_cfg']['check_env']

    def test_get_diff_checker_counts(self):
        """
        Test diff result types for new results.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.NEW)

        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # core.CallAndMessage is the new checker.
        test_res = {"core.NullDereference": 4}
        self.assertDictEqual(diff_dict, test_res)

    def test_get_diff_checker_counts_core_new(self):
        """
        Test diff result types for new core checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.NEW)
        report_filter = ReportFilter(checkerName=["*core*"])
        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    report_filter,
                                                    cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # core.CallAndMessage is the new checker.
        test_res = {"core.NullDereference": 4}
        self.assertDictEqual(diff_dict, test_res)

    def test_get_diff_res_count_new_no_base(self):
        """
        Count the new results with no filter and no baseline
        run ids.
        """
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.NEW)

        diff_res = self._cc_client.getRunResultCount([],
                                                     ReportFilter(),
                                                     cmp_data)
        # No differences.
        self.assertEqual(diff_res, 0)

    def test_get_diff_results_new(self):
        """
        Get the new results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.NEW)

        diff_res = self._cc_client.getRunResults([base_run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 ReportFilter(),
                                                 cmp_data,
                                                 False)
        # 4 new core.NullDereference issues.
        self.assertEqual(len(diff_res), 4)

    def test_get_diff_results_resolved(self):
        """
        Get the resolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.RESOLVED)

        diff_res = self._cc_client.getRunResults([base_run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 ReportFilter(),
                                                 cmp_data,
                                                 False)
        # 4 resolved core.CallAndMessage
        self.assertEqual(len(diff_res), 4)

    def test_get_diff_checker_counts_core_resolved(self):
        """
        Test diff result types for resolved core checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        report_filter = ReportFilter(checkerName=["*core*"])
        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.RESOLVED)
        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    report_filter,
                                                    cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # Resolved core checkers.
        test_res = {'core.CallAndMessage': 4}
        self.assertDictEqual(diff_dict, test_res)

    def test_get_diff_results_unresolved(self):
        """
        Get the unresolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        diff_res = self._cc_client.getRunResults([base_run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 ReportFilter(),
                                                 cmp_data,
                                                 False)
        self.assertEqual(len(diff_res), 26)

    def test_get_diff_checker_counts_core_unresolved(self):
        """
        Test diff result types for resolved unix checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        report_filter = ReportFilter(checkerName=["*core*"])
        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)
        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    report_filter,
                                                    cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # Unresolved core checkers.
        test_res = {'core.StackAddressEscape': 3, 'core.DivideZero': 11}
        self.assertLessEqual(test_res.items(), diff_dict.items())

    def test_get_diff_res_count_unresolved(self):
        """
        Count the unresolved results with no filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        base_count = self._cc_client.getRunResultCount([base_run_id],
                                                       ReportFilter(),
                                                       None)
        print("Base run id: %d", base_run_id)
        print("Base count: %d", base_count)

        base_run_res = get_all_run_results(self._cc_client, base_run_id)

        print_run_results(base_run_res)

        new_count = self._cc_client.getRunResultCount([new_run_id],
                                                      ReportFilter(),
                                                      None)
        print("New run id: %d", new_run_id)
        print("New count: %d", new_count)

        new_run_res = get_all_run_results(self._cc_client, new_run_id)

        print_run_results(new_run_res)

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        diff_res = self._cc_client.getRunResultCount([base_run_id],
                                                     ReportFilter(),
                                                     cmp_data)

        self.assertEqual(diff_res, 26)

    def test_get_diff_res_count_unresolved_filter(self):
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        filter_severity_levels = [{"MEDIUM": 1}, {"LOW": 6},
                                  {"HIGH": 19}, {"STYLE": 0},
                                  {"CRITICAL": 0}]

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        for level in filter_severity_levels:
            for severity_level, test_result_count in level.items():
                sev = get_severity_level(severity_level)
                sev_filter = ReportFilter(severity=[sev])

                diff_result_count = self._cc_client.getRunResultCount(
                    [base_run_id], sev_filter, cmp_data)

                self.assertEqual(test_result_count, diff_result_count)

    def test_get_diff_checker_counts_all_unresolved(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        # All unresolved checkers.
        test_res = {'unix.Malloc': 1,
                    'cplusplus.NewDelete': 5,
                    'deadcode.DeadStores': 6,
                    'core.StackAddressEscape': 3,
                    'core.DivideZero': 11}
        self.assertLessEqual(diff_dict.items(), test_res.items())

    def test_get_diff_severity_counts_all_unresolved(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        sev_res = self._cc_client.getSeverityCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data)
        test_res = {Severity.HIGH: 19,
                    Severity.LOW: 6,
                    Severity.MEDIUM: 1}
        self.assertDictEqual(sev_res, test_res)

    def test_get_diff_severity_counts_all_new(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.NEW)

        sev_res = self._cc_client.getSeverityCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data)
        test_res = {Severity.HIGH: 4}
        self.assertDictEqual(sev_res, test_res)

    def test_get_diff_new_review_status_counts(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.NEW)

        res = self._cc_client.getReviewStatusCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data)

        test_res = {ReviewStatus.UNREVIEWED: 4}
        self.assertDictEqual(res, test_res)

    def test_get_diff_unres_review_status_counts(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        res = self._cc_client.getReviewStatusCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data)

        test_res = {ReviewStatus.UNREVIEWED: 26}
        self.assertDictEqual(res, test_res)

    def test_get_diff_res_review_status_counts(self):
        """
        Test diff result types for all unresolved checker counts.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.RESOLVED)

        res = self._cc_client.getReviewStatusCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data)

        print(res)
        test_res = {ReviewStatus.UNREVIEWED: 4}
        self.assertDictEqual(res, test_res)

    def test_get_diff_res_types_resolved(self):
        """
        Test diff result types for resolved results.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.RESOLVED)

        diff_res = self._cc_client.getCheckerCounts([base_run_id],
                                                    ReportFilter(),
                                                    cmp_data,
                                                    None,
                                                    0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        test_res = {'core.CallAndMessage': 4}
        self.assertDictEqual(diff_dict, test_res)

    def test_get_diff_res_types_unresolved(self):
        """
        Test diff result types for unresolved results with no filter
        on the api.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        diff_res = \
            self._cc_client.getCheckerCounts([base_run_id],
                                             ReportFilter(),
                                             cmp_data,
                                             None,
                                             0)
        diff_dict = dict((res.name, res.count) for res in diff_res)

        test_res = {'unix.Malloc': 1,
                    'cplusplus.NewDelete': 5,
                    'deadcode.DeadStores': 6,
                    'core.StackAddressEscape': 3,
                    'core.DivideZero': 11}
        self.assertDictEqual(diff_dict, test_res)

    def test_get_diff_res_types_unresolved_filter(self):
        """
        Test diff result types for unresolved results with filter.
        """
        base_run_id = self._base_runid
        new_run_id = self._new_runid

        diff_res_types_filter = self._testproject_data[self._clang_to_test][
            'diff_res_types_filter']

        cmp_data = CompareData(runIds=[new_run_id],
                               diffType=DiffType.UNRESOLVED)

        for level in diff_res_types_filter:
            for checker_name, test_result_count in level.items():
                checker_filter = ReportFilter(checkerName=[checker_name])
                diff_res = \
                    self._cc_client.getCheckerCounts([base_run_id],
                                                     checker_filter,
                                                     cmp_data,
                                                     None,
                                                     0)
                diff_dict = dict((res.name, res.count) for res in diff_res)

                # There should be only one result for each checker name.
                self.assertEqual(test_result_count, diff_dict[checker_name])

    def test_cmd_compare_remote_res_count_new_rgx(self):
        """Count the new results with no filter, use regex in the run name."""
        base_run_name = self._test_runs[0].name
        new_run_name = self._test_runs[1].name

        # Change test_files_blablabla to test_*_blablabla
        new_run_name = new_run_name.replace('files', '*')

        out = get_diff_results([base_run_name], [new_run_name], '--resolved',
                               None, ["--url", self._url], self._env)

        # 4 disappeared core.CallAndMessage issues
        count = len(re.findall(r'\[core\.CallAndMessage\]', out[0]))
        self.assertEqual(count, 4)

    def test_diff_to_tag(self):
        """Count remote diff compared to tag."""
        report_dir = os.path.join(
            self._testproject_data['project_path_update'],
            'reports')
        run_name = self._test_runs[2].name

        out = get_diff_results([f'{run_name}:t1'], [report_dir],
                               '--new', 'json', ["--url", self._url])
        self.assertEqual(len(out[0]), 5)

        out = get_diff_results([f'{run_name}:t2'], [report_dir],
                               '--new', 'json', ["--url", self._url])
        self.assertEqual(len(out[0]), 0)

        out = get_diff_results([f'{run_name}:t1'], [report_dir],
                               '--unresolved', 'json', ["--url", self._url])
        self.assertEqual(len(out[0]), 27)

        out = get_diff_results([f'{run_name}:t2'], [report_dir],
                               '--unresolved', 'json', ["--url", self._url])
        self.assertEqual(len(out[0]), 32)

        out = get_diff_results([f'{run_name}:t1'], [report_dir],
                               '--resolved', 'json', ["--url", self._url])
        self.assertEqual(len(out[0]), 0)

        out = get_diff_results([f'{run_name}:t2'], [report_dir],
                               '--resolved', 'json', ["--url", self._url])
        self.assertEqual(len(out[0]), 0)

    def test_diff_between_literal_colon_in_name(self):
        """Count remote diff compared to a name which contains a literal ':'
        but does not refer to a tag.
        """
        # Name order matters from __init__ !
        base_to_new = get_diff_results([self._test_runs[0].name],
                                       [self._test_runs[1].name],
                                       '--new', 'json', ["--url", self._url])

        colon_base_name = self._test_runs[0].name + r"\:base"
        colon_new_name = self._test_runs[1].name + r"\:new"

        colon_base_to_new = get_diff_results([colon_base_name],
                                             [colon_new_name],
                                             '--new', 'json',
                                             ["--url", self._url])

        self.assertEqual(len(base_to_new[0]), len(colon_base_to_new[0]))

    def test_max_compound_select(self):
        """Test the maximum number of compound select query."""
        base_run_id = self._test_runs[0].runId

        report_hashes = [str(i) for i in range(0, 10000)]
        diff_res = self._cc_client.getDiffResultsHash([base_run_id],
                                                      report_hashes,
                                                      DiffType.NEW,
                                                      None,
                                                      None)
        self.assertEqual(len(diff_res), len(report_hashes))

    def test_diff_run_tags(self):
        """Test for diff runs by run tags."""
        run_id = self._update_runid

        def get_run_tags(tag_name):
            run_history_filter = RunHistoryFilter(tagNames=[tag_name])
            return self._cc_client.getRunHistory([run_id], None, None,
                                                 run_history_filter)

        get_all_tags = get_run_tags('t*')
        self.assertEqual(len(get_all_tags), 3)

        base_tags = get_run_tags('t1')
        self.assertEqual(len(base_tags), 1)
        base_tag_id = base_tags[0].id

        new_tags = get_run_tags('t2')
        self.assertEqual(len(new_tags), 1)
        new_tag_id = new_tags[0].id

        tag_filter = ReportFilter(runTag=[base_tag_id])
        cmp_data = CompareData(runIds=[run_id],
                               diffType=DiffType.NEW,
                               runTag=[new_tag_id])

        diff_res = self._cc_client.getRunResults([run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 tag_filter,
                                                 cmp_data,
                                                 False)

        # 5 new core.CallAndMessage issues (as the checker was enabled from
        # tag1 to tag2).
        self.assertEqual(len(diff_res), 5)

        cmp_data.diffType = DiffType.RESOLVED
        diff_res = self._cc_client.getRunResults([run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 tag_filter,
                                                 cmp_data,
                                                 False)

        # 3 core.StackAddressEscape reports are resolved (as the checker was
        # disabled from tag1 to tag2).
        self.assertEqual(len(diff_res), 3)

        cmp_data.diffType = DiffType.UNRESOLVED
        diff_res = self._cc_client.getRunResults([run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 tag_filter,
                                                 cmp_data,
                                                 False)
        self.assertEqual(len(diff_res), 27)

    def test_only_open_report_date_filter_is_set(self):
        """ Test if only the open reports date filter is set for the baseline,
        and the date is really old there will be no reports.
        """
        d = datetime(1992, 1, 1)
        tag_filter = ReportFilter(openReportsDate=int(d.timestamp()))
        res = self._cc_client.getRunResults(None, 500, 0, [], tag_filter,
                                            None, False)

        self.assertEqual(len(res), 0)

    def test_diff_open_reports_date(self):
        """Test for diff results by open reports date."""
        run_id = self._update_runid

        def get_run_tags(tag_name):
            run_history_filter = RunHistoryFilter(tagNames=[tag_name])
            return self._cc_client.getRunHistory([run_id], None, None,
                                                 run_history_filter)

        get_all_tags = get_run_tags('t*')
        self.assertEqual(len(get_all_tags), 3)

        base_tags = get_run_tags('t1')
        self.assertEqual(len(base_tags), 1)
        base_tag_time = str_to_date(base_tags[0].time) + timedelta(0, 1)
        base_tag_timestamp = int(base_tag_time.timestamp())

        new_tags = get_run_tags('t2')
        self.assertEqual(len(new_tags), 1)
        new_tag_time = str_to_date(new_tags[0].time) + timedelta(0, 1)
        new_tag_timestamp = int(new_tag_time.timestamp())

        tag_filter = ReportFilter(openReportsDate=base_tag_timestamp)
        cmp_data = CompareData(runIds=[run_id],
                               diffType=DiffType.NEW,
                               openReportsDate=new_tag_timestamp)

        diff_res = self._cc_client.getRunResults([run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 tag_filter,
                                                 cmp_data,
                                                 False)

        # 5 new core.CallAndMessage issues (as the checker was enabled from
        # tag1 to tag2).
        self.assertEqual(len(diff_res), 5)

        cmp_data.diffType = DiffType.RESOLVED
        diff_res = self._cc_client.getRunResults([run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 tag_filter,
                                                 cmp_data,
                                                 False)

        # 3 core.StackAddressEscape reports are resolved (as the checker was
        # disabled from tag1 to tag2).
        self.assertEqual(len(diff_res), 3)

        cmp_data.diffType = DiffType.UNRESOLVED
        diff_res = self._cc_client.getRunResults([run_id],
                                                 500,
                                                 0,
                                                 [],
                                                 tag_filter,
                                                 cmp_data,
                                                 False)
        self.assertEqual(len(diff_res), 27)

    def test_multiple_runs(self):
        """ Count the unresolved results in multiple runs without filter. """
        base_run_name = self._test_runs[0].name
        new_run_name = self._test_runs[1].name

        unresolved_results = \
            get_diff_results([base_run_name, new_run_name],
                             [new_run_name, base_run_name],
                             '--unresolved', 'json', ["--url", self._url])

        self.assertNotEqual(len(unresolved_results[0]), 0)

    def test_source_line_content(self):
        """
        Check that line / file contents are set properly for different
        output types.
        """
        base_run_name = self._test_runs[0].name
        new_run_name = self._test_runs[1].name

        html_reports = os.path.join(self.test_workspace, "html_reports")

        base_run_names = [base_run_name, new_run_name]
        new_run_names = [new_run_name, base_run_name]
        extra_args = [
            "--url", self._url,
            "--file", "*/divide_zero.cpp",
            "--checker-name", "core.DivideZero",
            "--output", "plaintext", "html",
            '--export-dir', html_reports]

        # Check plain text output.
        out, _, _ = \
            get_diff_results(base_run_names, new_run_names,
                             '--unresolved', None, extra_args)

        lines = out.split(os.linesep)
        for idx, line in enumerate(lines):
            if '[core.DivideZero]' in line:
                self.assertTrue(lines[idx + 1].strip(), "Invalid line content")

        # Check HTML output
        for file_path in os.listdir(html_reports):
            with open(os.path.join(html_reports, file_path),
                      encoding='utf-8') as f:
                self.assertNotIn(InvalidFileContentMsg, f.read())

        shutil.rmtree(html_reports, ignore_errors=True)

    def test_print_bug_steps(self):
        """ Test printing the steps the analyzers took. """
        base_run_name = self._test_runs[0].name
        new_run_name = self._test_runs[1].name

        out, _, ret = get_diff_results(
            [base_run_name], [new_run_name], '--resolved', None,
            ["--url", self._url, "--print-steps"])

        self.assertTrue("Steps:" in out)
        self.assertTrue("Report hash:" in out)
        self.assertEqual(ret, 2)
