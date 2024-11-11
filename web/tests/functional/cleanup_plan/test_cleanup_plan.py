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
import shutil
import sys
import uuid
import time
import unittest

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CleanupPlanFilter, \
    ReportFilter

from libtest import codechecker
from libtest import env
from libtest import project
from libtest.thrift_client_to_db import get_all_run_results


class TestComment(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for the tests. """

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('cleanup_plan')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_project = 'cpp'

        test_project_path = project.path(test_project)

        test_config = {}

        project_info = project.get_info(test_project)

        test_config['test_project'] = project_info
        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'reportdir': os.path.join(TEST_WORKSPACE, 'reports'),
            'checkers': []
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'cleanup_plan'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Check the test project for the first time.
        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex
        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name,
                                          test_project_path)
        if ret:
            sys.exit(1)
        print("Analyzing test project was successful.")

        codechecker_cfg['run_names'] = [test_project_name]
        test_config['codechecker_cfg'] = codechecker_cfg
        env.export_test_cfg(TEST_WORKSPACE, test_config)

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
