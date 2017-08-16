#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

from collections import Counter
import os
import unittest

import shared
from shared.ttypes import ReviewStatus
from shared.ttypes import Severity
from shared.ttypes import DetectionStatus
from codeCheckerDBAccess.ttypes import ReportFilter_v2

from libtest import env


def get_severity_level(name):
    """ Convert severity name to value. """
    return shared.ttypes.Severity._NAMES_TO_VALUES[name]


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

        runs = self._cc_client.getRunData(None)

        test_runs = [run for run in runs if run.name in run_names]
        self._runids = [r.runId for r in test_runs]

        self.run1_checkers = \
            {'core.CallAndMessage': 5,
             'core.DivideZero': 3,
             'core.NullDereference': 4,
             'core.StackAddressEscape': 3,
             'cplusplus.NewDelete': 5,
             'deadcode.DeadStores': 5,
             'unix.Malloc': 1}

        self.run2_checkers = \
            {'core.CallAndMessage': 5,
             'core.DivideZero': 3,
             'core.NullDereference': 4,
             'cplusplus.NewDelete': 5,
             'deadcode.DeadStores': 5,
             'unix.MismatchedDeallocator': 1}

        self.run1_sev_counts = {Severity.MEDIUM: 1,
                                Severity.LOW: 5,
                                Severity.HIGH: 20}

        self.run2_sev_counts = {Severity.MEDIUM: 1,
                                Severity.LOW: 5,
                                Severity.HIGH: 17}

        self.run1_detection_counts = \
            {DetectionStatus.NEW: 26}

        self.run2_detection_counts = \
            {DetectionStatus.NEW: 23}

        self.run1_files = \
            {'file_to_be_skipped.cpp': 2,
             'null_dereference.cpp': 5,
             'new_delete.cpp': 6,
             'stack_address_escape.cpp': 3,
             'call_and_message.cpp': 5,
             'divide_zero.cpp': 4,
             'has a space.cpp': 1
             }

        self.run2_files = \
            {'call_and_message.cpp': 5,
             'new_delete.cpp': 6,
             'divide_zero.cpp': 4,
             'null_dereference.cpp': 5,
             'file_to_be_skipped.cpp': 2,
             'has a space.cpp': 1
             }

        self.run1_checker_msg = \
            {"Argument to 'delete' is the address of the local variable 'i', "
             "which is not memory allocated by 'new'": 1,
             'Called function pointer is null (null dereference)': 1,
             "Value stored to 'k' during its initialization is never read": 1,
             "Dereference of null pointer (loaded from variable 'p')": 2,
             'Division by zero': 3,
             'Use of memory after it is freed': 2,
             "Array access (from variable 'p') results in a null pointer "
             "dereference": 1,
             "Address of stack memory associated with local variable 'y' is "
             "still referred to by the global variable 'x' upon returning to "
             "the caller.  This will be a dangling reference": 1,
             "Address of stack memory associated with local variable 'str' is "
             "still referred to by the global variable 'p' upon returning to "
             "the caller.  This will be a dangling reference": 1,
             'Called function pointer is an uninitalized pointer value': 1,
             'Called C++ object pointer is null': 1,
             'Address of stack memory allocated by call to alloca() on line '
             '18 returned to caller': 1,
             'Called C++ object pointer is uninitialized': 1,
             "Argument to 'delete[]' is offset by 4 bytes from the start of "
             "memory allocated by 'new[]'": 1,
             'Attempt to free released memory': 1,
             "Access to field 'x' results in a dereference of a null pointer "
             "(loaded from variable 'pc')": 1,
             "Passed-by-value struct argument contains uninitialized data "
             "(e.g., field: 'x')": 1,
             'Memory allocated by alloca() should not be deallocated': 1,
             "Value stored to 'y' during its initialization is never read": 1,
             "Value stored to 'x' during its initialization is never read": 3}

        self.run2_checker_msg = \
            {"Argument to 'delete' is the address of the local variable "
             "'i', which is not memory allocated by 'new'": 1,
             'Called function pointer is null (null dereference)': 1,
             "Value stored to 'k' during its initialization is "
             "never read": 1,
             "Dereference of null pointer (loaded from variable 'p')": 2,
             'Division by zero': 3,
             'Use of memory after it is freed': 2,
             'Called C++ object pointer is null': 1,
             "Value stored to 'y' during its initialization is "
             "never read": 1,
             'Called function pointer is an uninitalized pointer '
             'value': 1,
             "Array access (from variable 'p') results in a null "
             "pointer dereference": 1,
             "Passed-by-value struct argument contains uninitialized "
             "data (e.g., field: 'x')": 1,
             'Called C++ object pointer is uninitialized': 1,
             "Argument to 'delete[]' is offset by 4 bytes from the start "
             "of memory allocated by 'new[]'": 1,
             'Attempt to free released memory': 1,
             "Access to field 'x' results in a dereference of a null "
             "pointer (loaded from variable 'pc')": 1,
             'Memory allocated by alloca() should not be deallocated': 1,
             "Value stored to 'x' during its initialization "
             "is never read": 3}

    def test_run1_all_checkers(self):
        """
        Get all the checker counts for run1.
        """
        runid = self._runids[0]
        checker_counts = self._cc_client.getCheckerCounts([runid],
                                                          None,
                                                          None)

        self.assertEqual(len(checker_counts), len(self.run1_checkers))
        self.assertDictEqual(checker_counts, self.run1_checkers)

    def test_run1_core_checkers(self):
        """
        Get all the core checker counts for run1.
        """
        runid = self._runids[0]
        core_filter = ReportFilter_v2(checkerName=["core*"])
        checker_counts = self._cc_client.getCheckerCounts([runid],
                                                          core_filter,
                                                          None)
        core_checkers = {k: v for k, v in self.run1_checkers.items()
                         if "core." in k}

        self.assertEqual(len(checker_counts), len(core_checkers))
        self.assertDictEqual(checker_counts, core_checkers)

    def test_run2_all_checkers(self):
        """
        Get all the checker counts for run2.
        """
        runid = self._runids[1]
        checker_counts = self._cc_client.getCheckerCounts([runid],
                                                          None,
                                                          None)

        print(checker_counts)
        self.assertEqual(len(checker_counts), len(self.run2_checkers))
        self.assertDictEqual(checker_counts, self.run2_checkers)

    def test_run1_run2_all_checkers(self):
        """
        Get all the checker counts for run1 and run2.
        """
        checker_counts = self._cc_client.getCheckerCounts(self._runids,
                                                          None,
                                                          None)

        r1_checkers = Counter(self.run1_checkers)
        r2_checkers = Counter(self.run2_checkers)
        all_checkers = dict(r1_checkers + r2_checkers)

        self.assertEqual(len(checker_counts), len(all_checkers))
        self.assertDictEqual(checker_counts, all_checkers)

    def test_run1_run2_core_checkers(self):
        """
        Get all the core checker counts for run1 and run2.
        """
        core_filter = ReportFilter_v2(checkerName=["core*"])
        checker_counts = self._cc_client.getCheckerCounts(self._runids,
                                                          core_filter,
                                                          None)

        core_checkers_r1 = {k: v for k, v in self.run1_checkers.items()
                            if "core." in k}

        core_checkers_r2 = {k: v for k, v in self.run2_checkers.items()
                            if "core." in k}

        r1_core = Counter(core_checkers_r1)
        r2_core = Counter(core_checkers_r2)
        all_core = dict(r1_core + r2_core)

        self.assertEqual(len(checker_counts), len(all_core))
        self.assertDictEqual(checker_counts, all_core)

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
        file_counts = self._cc_client.getFileCounts([runid], None, None)
        res = {get_filename(k): v for k, v in file_counts.items()}

        print(res)
        self.assertEqual(len(res), len(self.run1_files))
        self.assertDictEqual(res, self.run1_files)

    def test_run2_all_file(self):
        """
        Get all the file counts for run2.
        """
        runid = self._runids[1]
        file_counts = self._cc_client.getFileCounts([runid], None, None)
        res = {get_filename(k): v for k, v in file_counts.items()}

        print(res)
        self.assertEqual(len(res), len(self.run2_files))
        self.assertDictEqual(res, self.run2_files)

    def test_run1_run2_all_file(self):
        """
        Get all the file counts for run1 and run2.
        """
        file_counts = self._cc_client.getFileCounts(self._runids, None, None)
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
        null_stack_filter = ReportFilter_v2(
            filepath=["*null_dereference.cpp", "*stack_address_escape.cpp"])

        file_counts = self._cc_client.getFileCounts(self._runids,
                                                    null_stack_filter,
                                                    None)

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

        self.assertEqual(len(res), len(test_res))
        self.assertDictEqual(res, test_res)

    def test_run1_all_checker_msg(self):
        """
        Get all the file checker messages for for run1.
        """
        runid = self._runids[0]
        msg_counts = self._cc_client.getCheckerMsgCounts([runid],
                                                         None,
                                                         None)

        print(msg_counts)
        self.assertEqual(len(msg_counts), len(self.run1_checker_msg))
        self.assertDictEqual(msg_counts, self.run1_checker_msg)

    def test_run2_all_checker_msg(self):
        """
        Get all the file checker messages for for run2.
        """
        runid = self._runids[1]
        msg_counts = self._cc_client.getCheckerMsgCounts([runid],
                                                         None,
                                                         None)

        self.assertEqual(len(msg_counts), len(self.run2_checker_msg))
        self.assertDictEqual(msg_counts, self.run2_checker_msg)

    def test_run1_run2_all_checker_msg(self):
        """
        Get all the file checker messages for run1 and run2.
        """
        file_counts = self._cc_client.getCheckerMsgCounts(self._runids,
                                                          None,
                                                          None)
        res = {get_filename(k): v for k, v in file_counts.items()}

        r1_checker_msg = Counter(self.run1_checker_msg)
        r2_checker_msg = Counter(self.run2_checker_msg)
        all_checker_msg = dict(r1_checker_msg + r2_checker_msg)

        print(res)

        self.assertEqual(len(res), len(all_checker_msg))
        self.assertDictEqual(res, all_checker_msg)

    def test_run1_all_review_status(self):
        """
        Get all the file checker messages for for run1.
        """
        runid = self._runids[0]

        report_count = self._cc_client.getRunResultCount([runid], [])

        report_ids = [x.reportId for x in self._cc_client.getRunResults(
                      [runid], report_count, 0, [], [])]

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
                                               ReviewStatus.WONT_FIX,
                                               'comment')

        # Unset statuses cout as unreviewed.
        review_status = {ReviewStatus.CONFIRMED: 5,
                         ReviewStatus.UNREVIEWED: 11,
                         ReviewStatus.FALSE_POSITIVE: 5,
                         ReviewStatus.WONT_FIX: 5}

        rv_counts = self._cc_client.getReviewStatusCounts([runid], None, None)

        self.assertEqual(len(rv_counts), len(review_status))
        self.assertDictEqual(rv_counts, review_status)

    def test_run1_run2_all_review_status(self):
        """
        Get all the file checker messages for for run1.
        """
        runid = self._runids[0]

        report_count = self._cc_client.getRunResultCount([runid], [])

        report_ids = [x.reportId for x
                      in self._cc_client.getRunResults([runid],
                                                       report_count,
                                                       0,
                                                       [],
                                                       [])]

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
                                               ReviewStatus.WONT_FIX,
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
                             dict(Counter(rv_counts_1)+Counter(rv_counts_2)))

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
        new_filter = ReportFilter_v2(
                detectionStatus=[shared.ttypes.DetectionStatus.NEW])
        new_reports = self._cc_client.getCheckerCounts([runid],
                                                       new_filter,
                                                       None)
        new = {'core.CallAndMessage': 5,
               'core.StackAddressEscape': 3,
               'cplusplus.NewDelete': 5,
               'core.NullDereference': 4,
               'core.DivideZero': 3,
               'deadcode.DeadStores': 5,
               'unix.Malloc': 1}
        self.assertDictEqual(new, new_reports)

    def test_run1_detection_status_resolved(self):
        """
        Get all the resolved checker counts for run1.
        """

        runid = self._runids[0]
        resolved_filter = ReportFilter_v2(
                detectionStatus=[shared.ttypes.DetectionStatus.RESOLVED])
        resolved_reports = self._cc_client.getCheckerCounts([runid],
                                                            resolved_filter,
                                                            None)
        self.assertDictEqual({}, resolved_reports)

    def test_run1_detection_status_unresolved(self):
        """
        Get all the unresolved checker counts for run1.
        """

        runid = self._runids[0]
        unresolved_filter = ReportFilter_v2(
                detectionStatus=[shared.ttypes.DetectionStatus.UNRESOLVED])
        unresolved_reports = \
            self._cc_client.getCheckerCounts([runid],
                                             unresolved_filter,
                                             None)
        self.assertDictEqual({}, unresolved_reports)

    def test_run1_detection_status_repoened(self):
        """
        Get all the reopened checker counts for run1.
        """

        runid = self._runids[0]
        reopen_filter = ReportFilter_v2(
                detectionStatus=[shared.ttypes.DetectionStatus.REOPENED])
        reopened_reports = self._cc_client.getCheckerCounts([runid],
                                                            reopen_filter,
                                                            None)
        self.assertDictEqual({}, reopened_reports)
