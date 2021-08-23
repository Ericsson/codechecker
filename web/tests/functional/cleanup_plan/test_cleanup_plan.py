#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Report commenting tests.
"""


import datetime
import os
import time
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CleanupPlanFilter, \
    ReportFilter

from libtest import env
from libtest.thrift_client_to_db import get_all_run_results


class TestComment(unittest.TestCase):

    def setUp(self):
        self._test_workspace = os.environ.get('TEST_WORKSPACE')

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self._test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

    def test_managing_cleanup_plans(self):
        """ Test managing cleanup plans. """
        cleanup_plans = self._cc_client.getCleanupPlans(None)
        self.assertFalse(cleanup_plans)

        due_date = datetime.date.today() + datetime.timedelta(days=1)
        due_date_timestamp = int(time.mktime(due_date.timetuple()))

        data = [
            ("Test", "Test description", due_date_timestamp),
            ("Dummy", None, None),
        ]

        cleanup_plan_id = {}
        for name, description, due_date in data:
            cleanup_plan_id[name] = self._cc_client.addCleanupPlan(
                name, description, due_date)

        # Get all cleanup plans.
        cleanup_plans = self._cc_client.getCleanupPlans(None)
        self.assertEqual(len(cleanup_plans), 2)

        self.assertEqual(cleanup_plans[0].name, data[1][0])
        self.assertEqual(cleanup_plans[0].description, data[1][1])
        self.assertEqual(cleanup_plans[0].dueDate, data[1][2])
        self.assertEqual(cleanup_plans[0].closedAt, None)
        self.assertEqual(cleanup_plans[0].reportHashes, [])

        self.assertEqual(cleanup_plans[1].name, data[0][0])
        self.assertEqual(cleanup_plans[1].description, data[0][1])
        self.assertEqual(cleanup_plans[1].dueDate, data[0][2])
        self.assertEqual(cleanup_plans[1].closedAt, None)
        self.assertEqual(cleanup_plans[1].reportHashes, [])

        # Filter cleanup plans.
        cleanup_plan_filter = CleanupPlanFilter(names=[data[0][0]])
        cleanup_plans = self._cc_client.getCleanupPlans(cleanup_plan_filter)
        self.assertEqual(len(cleanup_plans), 1)
        self.assertEqual(cleanup_plans[0].name, data[0][0])

        # Close a cleanup plan and filter out closed cleanup plans.
        success = self._cc_client.closeCleanupPlan(cleanup_plan_id[data[0][0]])
        self.assertTrue(success)

        cleanup_plans = self._cc_client.getCleanupPlans(None)
        self.assertEqual(len(cleanup_plans), 2)

        cleanup_plan_filter = CleanupPlanFilter(
            names=[data[0][0]], isOpen=False)
        cleanup_plans = self._cc_client.getCleanupPlans(cleanup_plan_filter)
        self.assertEqual(len(cleanup_plans), 1)
        self.assertTrue(cleanup_plans[0].closedAt)

        # Reopen cleanup plan.
        success = self._cc_client.reopenCleanupPlan(
            cleanup_plan_id[data[0][0]])
        self.assertTrue(success)

        cleanup_plan_filter = CleanupPlanFilter(names=[data[0][0]])
        cleanup_plans = self._cc_client.getCleanupPlans(cleanup_plan_filter)
        self.assertEqual(len(cleanup_plans), 1)
        self.assertEqual(cleanup_plans[0].name, data[0][0])
        self.assertFalse(cleanup_plans[0].closedAt)

        # Remove cleanups.
        success = self._cc_client.removeCleanupPlan(
            cleanup_plan_id[data[0][0]])
        self.assertTrue(success)

        success = self._cc_client.removeCleanupPlan(
            cleanup_plan_id[data[1][0]])
        self.assertTrue(success)

        cleanup_plans = self._cc_client.getCleanupPlans(None)
        self.assertFalse(len(cleanup_plans))

    def test_assign_reports_to_cleanup_plans(self):
        """ Test assigning reports to cleanup plans. """
        name = "Test"
        description = None
        due_date = None

        cleanup_plan_id = self._cc_client.addCleanupPlan(
            name, description, due_date)

        # Get all cleanup plans.
        cleanup_plans = self._cc_client.getCleanupPlans(None)
        self.assertEqual(len(cleanup_plans), 1)

        cleanup_plan = cleanup_plans[0]
        self.assertEqual(cleanup_plan.reportHashes, [])

        # Get results from the database.
        run_results = get_all_run_results(self._cc_client)
        self.assertTrue(run_results)

        uniqued_report_hashes = set(r.bugHash for r in run_results)
        self.assertTrue(len(uniqued_report_hashes) > 2)

        it = iter(uniqued_report_hashes)
        report_hash_1 = next(it)
        report_hash_2 = next(it)
        report_hashes = [report_hash_1, report_hash_2]

        # Assign report to cleanup.
        success = self._cc_client.setCleanupPlan(
            cleanup_plan_id, report_hashes)
        self.assertTrue(success)

        cleanup_plans = self._cc_client.getCleanupPlans(None)
        cleanup_plan = cleanup_plans[0]
        self.assertCountEqual(
            cleanup_plan.reportHashes, report_hashes)

        # Filter reports based on cleanup plan.
        report_filter = ReportFilter(cleanupPlanNames=[name])
        run_results = get_all_run_results(
            self._cc_client, filters=report_filter)
        self.assertTrue(run_results)

        for report in run_results:
            self.assertTrue(report.bugHash in report_hashes,
                            f"{report.bugHash} not found in cleanup plan.")

        # Remove report hash from cleanup plan.
        success = self._cc_client.unsetCleanupPlan(
            cleanup_plan_id, [report_hash_2])
        self.assertTrue(success)

        cleanup_plans = self._cc_client.getCleanupPlans(None)
        cleanup_plan = cleanup_plans[0]
        self.assertCountEqual(
            cleanup_plan.reportHashes, [report_hash_1])

        success = self._cc_client.unsetCleanupPlan(
            cleanup_plan_id, [report_hash_1])
        self.assertTrue(success)

        cleanup_plans = self._cc_client.getCleanupPlans(None)
        cleanup_plan = cleanup_plans[0]
        self.assertFalse(cleanup_plan.reportHashes)

        # Remove cleanup.
        success = self._cc_client.removeCleanupPlan(cleanup_plan_id)
        self.assertTrue(success)
