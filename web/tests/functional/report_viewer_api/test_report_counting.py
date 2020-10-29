#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test report counting.
"""


from collections import Counter
from collections import defaultdict
import os
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import DetectionStatus, \
    ReportFilter, ReviewStatus, Severity, RunSortMode, RunSortType, Order

from libtest import env


def get_severity_level(name):
    """ Convert severity name to value. """
    return Severity._NAMES_TO_VALUES[name]


def get_filename(path):
    _, filename = os.path.split(path)
    return filename


class TestReportFilter(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        test_workspace = os.environ['TEST_WORKSPACE']
        self.maxDiff = None

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

        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        runs = self._cc_client.getRunData(None, None, 0, sort_mode)

        self._test_runs = [run for run in runs if run.name in run_names]
        self._runids = [r.runId for r in self._test_runs]

        self.run1_checkers = \
            {'clang-diagnostic-division-by-zero': 3,
             'core.CallAndMessage': 5,
             'core.DivideZero': 10,
             'core.NullDereference': 4,
             'core.StackAddressEscape': 3,
             'cplusplus.NewDelete': 5,
             'deadcode.DeadStores': 6,
             'misc-definitions-in-headers': 2,
             'unix.Malloc': 1}

        self.run2_checkers = \
            {'clang-diagnostic-division-by-zero': 3,
             'core.CallAndMessage': 5,
             'core.DivideZero': 10,
             'core.NullDereference': 4,
             'cplusplus.NewDelete': 5,
             'deadcode.DeadStores': 6,
             'misc-definitions-in-headers': 2,
             'unix.MismatchedDeallocator': 1}

        self.run1_sev_counts = {Severity.MEDIUM: 6,
                                Severity.LOW: 6,
                                Severity.HIGH: 27}

        self.run2_sev_counts = {Severity.MEDIUM: 6,
                                Severity.LOW: 6,
                                Severity.HIGH: 24}

        self.run1_detection_counts = \
            {DetectionStatus.NEW: 39}

        self.run2_detection_counts = \
            {DetectionStatus.NEW: 36}

        self.run1_files = \
            {'file_to_be_skipped.cpp': 2,
             'null_dereference.cpp': 5,
             'new_delete.cpp': 6,
             'stack_address_escape.cpp': 3,
             'call_and_message.cpp': 5,
             'divide_zero.cpp': 5,
             'divide_zero_duplicate.cpp': 2,
             'has a space.cpp': 1,
             'skip_header.cpp': 2,
             'skip.h': 3,
             'path_begin.cpp': 2,
             'path_end.h': 3
             }

        self.run2_files = \
            {'call_and_message.cpp': 5,
             'new_delete.cpp': 6,
             'divide_zero.cpp': 5,
             'divide_zero_duplicate.cpp': 2,
             'null_dereference.cpp': 5,
             'file_to_be_skipped.cpp': 2,
             'has a space.cpp': 1,
             'skip_header.cpp': 2,
             'skip.h': 3,
             'path_begin.cpp': 2,
             'path_end.h': 3
             }

    def test_run1_all_checkers(self):
        """
        Get all the checker counts for run1.
        """
        runid = self._runids[0]
        checker_counts = self._cc_client.getCheckerCounts([runid],
                                                          None,
                                                          None,
                                                          None,
                                                          0)
        checkers_dict = dict((res.name, res.count) for res in checker_counts)

        self.assertGreaterEqual(len(checker_counts), len(self.run1_checkers))
        self.assertDictContainsSubset(self.run1_checkers, checkers_dict)

    def test_run1_core_checkers(self):
        """
        Get all the core checker counts for run1.
        """
        runid = self._runids[0]
        core_filter = ReportFilter(checkerName=["core*"])
        checker_counts = self._cc_client.getCheckerCounts([runid],
                                                          core_filter,
                                                          None,
                                                          None,
                                                          0)
        checkers_dict = dict((res.name, res.count) for res in checker_counts)

        core_checkers = {k: v for k, v in self.run1_checkers.items()
                         if "core." in k}

        self.assertGreaterEqual(len(checker_counts), len(core_checkers))
        self.assertDictContainsSubset(core_checkers, checkers_dict)

    def test_run2_all_checkers(self):
        """
        Get all the checker counts for run2.
        """
        runid = self._runids[1]
        checker_counts = self._cc_client.getCheckerCounts([runid],
                                                          None,
                                                          None,
                                                          None,
                                                          0)
        checkers_dict = dict((res.name, res.count) for res in checker_counts)

        self.assertGreaterEqual(len(checker_counts), len(self.run2_checkers))
        self.assertDictContainsSubset(self.run2_checkers, checkers_dict)

    def test_run1_run2_all_checkers(self):
        """
        Get all the checker counts for run1 and run2.
        """
        checker_counts = self._cc_client.getCheckerCounts(self._runids,
                                                          None,
                                                          None,
                                                          None,
                                                          0)
        checkers_dict = dict((res.name, res.count) for res in checker_counts)

        r1_checkers = Counter(self.run1_checkers)
        r2_checkers = Counter(self.run2_checkers)
        all_checkers = dict(r1_checkers + r2_checkers)

        self.assertEqual(len(checker_counts), len(all_checkers))
        self.assertDictEqual(checkers_dict, all_checkers)

    def test_run1_run2_core_checkers(self):
        """
        Get all the core checker counts for run1 and run2.
        """
        core_filter = ReportFilter(checkerName=["core*"])
        checker_counts = self._cc_client.getCheckerCounts(self._runids,
                                                          core_filter,
                                                          None,
                                                          None,
                                                          0)
        checkers_dict = dict((res.name, res.count) for res in checker_counts)

        core_checkers_r1 = {k: v for k, v in self.run1_checkers.items()
                            if "core." in k}

        core_checkers_r2 = {k: v for k, v in self.run2_checkers.items()
                            if "core." in k}

        r1_core = Counter(core_checkers_r1)
        r2_core = Counter(core_checkers_r2)
        all_core = dict(r1_core + r2_core)

        self.assertGreaterEqual(len(checker_counts), len(all_core))
        self.assertDictContainsSubset(all_core, checkers_dict)

    def test_run1_all_severity(self):
        """
        Get all the severity counts for run1.
        """
        runid = self._runids[0]
        severity_counts = self._cc_client.getSeverityCounts([runid],
                                                            None,
                                                            None)

        print(severity_counts)
        self.assertEqual(len(severity_counts), len(self.run1_sev_counts))
        self.assertDictEqual(severity_counts, self.run1_sev_counts)

    def test_run2_all_severity(self):
        """
        Get all the severity counts for run2.
        """
        runid = self._runids[1]
        severity_counts = self._cc_client.getSeverityCounts([runid],
                                                            None,
                                                            None)

        print(severity_counts)
        self.assertEqual(len(severity_counts), len(self.run2_sev_counts))
        self.assertDictEqual(severity_counts, self.run2_sev_counts)

    def test_run1_run2_all_severity(self):
        """
        Get all the severity counts for run1 and run2.
        """
        severity_counts = self._cc_client.getSeverityCounts(self._runids,
                                                            None,
                                                            None)
        r1_sev = Counter(self.run1_sev_counts)
        r2_sev = Counter(self.run2_sev_counts)
        all_sev = dict(r1_sev + r2_sev)

        print(severity_counts)
        self.assertEqual(len(severity_counts), len(all_sev))
        self.assertDictEqual(severity_counts, all_sev)

    def test_run1_all_file(self):
        """
        Get all the file counts for run1.
        """
        runid = self._runids[0]
        file_counts = self._cc_client.getFileCounts([runid], None, None, None,
                                                    0)
        res = {get_filename(k): v for k, v in file_counts.items()}

        print(res)
        self.assertEqual(len(res), len(self.run1_files))
        self.assertDictEqual(res, self.run1_files)

    def test_run2_all_file(self):
        """
        Get all the file counts for run2.
        """
        runid = self._runids[1]
        file_counts = self._cc_client.getFileCounts([runid], None, None, None,
                                                    0)
        res = {get_filename(k): v for k, v in file_counts.items()}

        print(res)
        self.assertEqual(len(res), len(self.run2_files))
        self.assertDictEqual(res, self.run2_files)

    def test_run1_run2_all_file(self):
        """
        Get all the file counts for run1 and run2.
        """
        file_counts = self._cc_client.getFileCounts(self._runids,
                                                    None,
                                                    None,
                                                    None,
                                                    0)
        res = {get_filename(k): v for k, v in file_counts.items()}

        r1_count = Counter(self.run1_files)
        r2_count = Counter(self.run2_files)
        all_res = dict(r1_count + r2_count)

        print(res)
        self.assertEqual(len(res), len(all_res))
        self.assertDictEqual(res, all_res)

    def test_run1_run2_file_filters(self):
        """
        Get all the core checker counts for run1 and run2.
        """
        null_stack_filter = ReportFilter(
            filepath=["*null_dereference.cpp", "*stack_address_escape.cpp"])

        file_counts = self._cc_client.getFileCounts(self._runids,
                                                    null_stack_filter,
                                                    None,
                                                    None,
                                                    0)

        res = {get_filename(k): v for k, v in file_counts.items()}

        null_r1 = {k: v for k, v in self.run1_files.items()
                   if "null_dereference" in k}

        stack_r1 = {k: v for k, v in self.run1_files.items()
                    if "stack_address_escape" in k}

        null_r2 = {k: v for k, v in self.run2_files.items()
                   if "null_dereference" in k}

        stack_r2 = {k: v for k, v in self.run2_files.items()
                    if "stack_address_escape" in k}

        test_res = dict(Counter(null_r1) + Counter(null_r2) +
                        Counter(stack_r1) + Counter(stack_r2))

        self.assertGreaterEqual(len(res), len(test_res))
        self.assertDictContainsSubset(test_res, res)

    def test_run1_run2_all_checker_msg(self):
        """
        Get all the file checker messages for run1 and run2.
        """
        run1_msgs = self._cc_client.getCheckerMsgCounts([self._runids[0]],
                                                        None,
                                                        None,
                                                        None,
                                                        0)

        run2_msgs = self._cc_client.getCheckerMsgCounts([self._runids[1]],
                                                        None,
                                                        None,
                                                        None,
                                                        0)

        run1_run2_msgs = self._cc_client.getCheckerMsgCounts(self._runids,
                                                             None,
                                                             None,
                                                             None,
                                                             0)

        r1_checker_msg = Counter(run1_msgs)
        r2_checker_msg = Counter(run2_msgs)
        all_checker_msg = dict(r1_checker_msg + r2_checker_msg)

        self.assertDictEqual(run1_run2_msgs, all_checker_msg)

    def test_run1_all_review_status(self):
        """
        Get all the file checker messages for for run1.
        """
        runid = self._runids[0]

        report_count = self._cc_client.getRunResultCount([runid],
                                                         None,
                                                         None)

        reports = self._cc_client.getRunResults(
            [runid], report_count, 0, [], None, None, False)

        reporthash_reports_count = dict(Counter([r.bugHash for r in reports]))

        bug_hashes = set()
        unique_reports = [bug_hashes.add(x.bugHash) or (x.reportId, x.bugHash)
                          for x in reports if x.bugHash not in bug_hashes]

        # Set report status of all reports to unreviewed.
        for report in reports:
            self._cc_client.changeReviewStatus(report.reportId,
                                               ReviewStatus.UNREVIEWED,
                                               '')

        review_status = defaultdict(int)
        review_status[ReviewStatus.UNREVIEWED] = len(reports)

        for i, status in enumerate([ReviewStatus.CONFIRMED,
                                    ReviewStatus.FALSE_POSITIVE,
                                    ReviewStatus.INTENTIONAL]):
            start_range = i * 5
            end_range = (i + 1) * 5
            for report in unique_reports[start_range:end_range]:
                self._cc_client.changeReviewStatus(report[0],
                                                   status,
                                                   'comment')
                review_status[status] += \
                    reporthash_reports_count[report[1]]

            review_status[ReviewStatus.UNREVIEWED] -= review_status[status]

        rv_counts = self._cc_client.getReviewStatusCounts([runid], None, None)

        review_status_dict = dict(review_status)
        self.assertEqual(len(rv_counts), len(review_status_dict))
        self.assertDictEqual(rv_counts, review_status_dict)

    def test_run1_run2_all_review_status(self):
        """
        Get all the file checker messages for for run1.
        """
        runid = self._runids[0]

        report_count = self._cc_client.getRunResultCount([runid],
                                                         None,
                                                         None)

        report_ids = [x.reportId for x
                      in self._cc_client.getRunResults([runid],
                                                       report_count,
                                                       0,
                                                       [],
                                                       None,
                                                       None,
                                                       False)]

        # Set report status of all reports to unreviewed.
        for rid in report_ids:
            self._cc_client.changeReviewStatus(rid,
                                               ReviewStatus.UNREVIEWED,
                                               '')

        for rid in report_ids[:5]:
            self._cc_client.changeReviewStatus(rid,
                                               ReviewStatus.UNREVIEWED,
                                               'comment')
        for rid in report_ids[5:10]:
            self._cc_client.changeReviewStatus(rid,
                                               ReviewStatus.CONFIRMED,
                                               'comment')

        for rid in report_ids[10:15]:
            self._cc_client.changeReviewStatus(rid,
                                               ReviewStatus.FALSE_POSITIVE,
                                               'comment')
        for rid in report_ids[15:20]:
            self._cc_client.changeReviewStatus(rid,
                                               ReviewStatus.INTENTIONAL,
                                               'comment')

        rv_counts_1 = self._cc_client.getReviewStatusCounts([self._runids[0]],
                                                            None,
                                                            None)

        rv_counts_2 = self._cc_client.getReviewStatusCounts([self._runids[1]],
                                                            None,
                                                            None)

        rv_counts_all = self._cc_client.getReviewStatusCounts(self._runids,
                                                              None,
                                                              None)

        self.assertDictEqual(rv_counts_all,
                             dict(Counter(rv_counts_1) + Counter(rv_counts_2)))

    def test_run1_all_detection_stats(self):
        """
        Get all the report detection statuses for run1.
        """
        runid = self._runids[0]
        detection_counts = \
            self._cc_client.getDetectionStatusCounts([runid], None, None)

        self.assertEqual(len(detection_counts),
                         len(self.run1_detection_counts))
        self.assertDictEqual(detection_counts, self.run1_detection_counts)

    def test_run2_all_detection_stats(self):
        """
        Get all the report detection statuses for run2.
        """
        runid = self._runids[1]
        detection_counts = \
            self._cc_client.getDetectionStatusCounts([runid], None, None)

        self.assertEqual(len(detection_counts),
                         len(self.run2_detection_counts))
        self.assertDictEqual(detection_counts, self.run2_detection_counts)

    def test_run1_run2_all_detection_stats(self):
        """
        Get all the report detection statuses for all the runs.
        """
        detection_counts = \
            self._cc_client.getDetectionStatusCounts(self._runids, None, None)

        r1_detection_counts = Counter(self.run1_detection_counts)
        r2_detection_counts = Counter(self.run2_detection_counts)
        all_detection_counts = dict(r1_detection_counts +
                                    r2_detection_counts)

        self.assertEqual(len(detection_counts),
                         len(all_detection_counts))
        self.assertDictEqual(detection_counts, all_detection_counts)

    def test_run1_detection_status_new(self):
        """
        Get all the new checker counts for run1.
        """
        runid = self._runids[0]
        new_filter = ReportFilter(
            detectionStatus=[DetectionStatus.NEW])
        new_reports = self._cc_client.getCheckerCounts([runid],
                                                       new_filter,
                                                       None,
                                                       None,
                                                       0)
        checkers_dict = dict((res.name, res.count) for res in new_reports)

        new = {'clang-diagnostic-division-by-zero': 3,
               'core.CallAndMessage': 5,
               'core.StackAddressEscape': 3,
               'cplusplus.NewDelete': 5,
               'core.NullDereference': 4,
               'core.DivideZero': 10,
               'deadcode.DeadStores': 6,
               'misc-definitions-in-headers': 2,
               'unix.Malloc': 1}
        self.assertDictEqual(new, checkers_dict)

    def test_run1_detection_status_resolved(self):
        """
        Get all the resolved checker counts for run1.
        """

        runid = self._runids[0]
        resolved_filter = ReportFilter(
            detectionStatus=[DetectionStatus.RESOLVED])
        resolved_reports = self._cc_client.getCheckerCounts([runid],
                                                            resolved_filter,
                                                            None,
                                                            None,
                                                            0)
        checkers_dict = dict((res.name, res.count) for res in resolved_reports)

        self.assertDictEqual({}, checkers_dict)

    def test_run1_detection_status_unresolved(self):
        """
        Get all the unresolved checker counts for run1.
        """

        runid = self._runids[0]
        unresolved_filter = ReportFilter(
            detectionStatus=[DetectionStatus.UNRESOLVED])
        unresolved_reports = \
            self._cc_client.getCheckerCounts([runid],
                                             unresolved_filter,
                                             None,
                                             None,
                                             0)
        checkers_dict = dict((res.name, res.count)
                             for res in unresolved_reports)

        self.assertDictEqual({}, checkers_dict)

    def test_run1_detection_status_repoened(self):
        """
        Get all the reopened checker counts for run1.
        """

        runid = self._runids[0]
        reopen_filter = ReportFilter(
            detectionStatus=[DetectionStatus.REOPENED])
        reopened_reports = self._cc_client.getCheckerCounts([runid],
                                                            reopen_filter,
                                                            None,
                                                            None,
                                                            0)
        checkers_dict = dict((res.name, res.count) for res in reopened_reports)
        self.assertDictEqual({}, checkers_dict)

    def test_all_run_report_counts(self):
        """
        Count the reports for all the runs.

        Run name is randomly generated for all of the test runs.
        """

        runs = self._cc_client.getRunData(None, None, 0, None)

        separate_report_counts = 0
        for run in runs:
            run_report_count = self._cc_client.getRunReportCounts(
                [run.runId], None, None, 0)
            # Should return the count for only one run.
            self.assertEqual(len(run_report_count), 1)
            separate_report_counts += run_report_count[0].reportCount

        all_report_counts = 0
        report_counts = \
            self._cc_client.getRunReportCounts([], None, None, 0)

        for rc in report_counts:
            all_report_counts += rc.reportCount

        self.assertEqual(separate_report_counts, all_report_counts)
