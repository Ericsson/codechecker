#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test review status functionality."""


import datetime
import logging
import os
import time
import unittest

from typing import Callable, List

from codechecker_api.codeCheckerDBAccess_v6.ttypes import CommentKind, \
    Order, ReviewStatus, ReviewStatusRule, ReviewStatusRuleFilter, \
    ReviewStatusRuleSortMode, ReviewStatusRuleSortType, RunFilter

from libtest import env, codechecker, plist_test, project
from libtest.thrift_client_to_db import get_all_run_results


class TestReviewStatus(unittest.TestCase):

    _ccClient = None

    def setUp(self):
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._testproject_data = env.setup_test_proj_cfg(self.test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test.
        run_names = env.get_run_names(self.test_workspace)
        # get the current run data
        run_filter = RunFilter(names=run_names, exactMatch=True)

        runs = self._cc_client.getRunData(run_filter, None, 0, None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 1,
                         'There should be only one run for this test, '
                         'with the given name configured at the test init.')
        self._runid = test_runs[0].runId

    def tearDown(self):
        """ Remove all review status rules after each test cases. """
        self.__remove_all_rules()

    def __get_system_comments(self, report_id):
        """ Get system comments for the given report id. """
        return [c for c in self._cc_client.getComments(report_id)
                if c.kind == CommentKind.SYSTEM]

    def __remove_all_rules(self):
        """ Removes all review status rules from the database. """
        self._cc_client.removeReviewStatusRules(None)

        # Check that there is no review status rule in the database.
        self.assertFalse(self._cc_client.getReviewStatusRulesCount(None))

        rules = self._cc_client.getReviewStatusRules(None, None, None, 0)
        self.assertFalse(rules)

    def __remove_all_comments(self, report_id):
        """ Removes all comments from the database. """
        comments = self._cc_client.getComments(report_id)
        for comment in comments:
            self.assertTrue(self._cc_client.removeComment(comment.id))

    def __check_value_order(self, values: List, order):
        """ Checks the order of the given values. """
        prev = None
        for value in values:
            if not prev:
                prev = value
                continue

            if order == Order.ASC:
                self.assertGreaterEqual(value, prev)
            else:
                self.assertLessEqual(value, prev)

    def __check_rule_order(
        self,
        field_selector: Callable[[ReviewStatusRule], None],
        sort_type: ReviewStatusRuleSortType
    ):
        """ Check review status rules order. """
        rule_filter = None
        limit = None
        offset = 0

        # Sort rules by the given sort type in descending order.
        sort_mode = ReviewStatusRuleSortMode(
            type=sort_type, ord=Order.DESC)
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.__check_value_order(
            [field_selector(r) for r in rules], Order.DESC)

        # Sort rules by the given sort type in ascending order.
        sort_mode = ReviewStatusRuleSortMode(
            type=sort_type, ord=Order.ASC)
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.__check_value_order(
            [field_selector(r) for r in rules], Order.ASC)

    def test_multiple_change_review_status(self):
        """
        Test changing review status of the same bug.
        """
        runid = self._runid
        run_results = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug = run_results[0]

        self.__remove_all_comments(bug.reportId)

        # There are no system comments for this bug.
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 0)

        # Change review status to confirmed bug.
        review_comment = 'This is really a bug'
        status = ReviewStatus.CONFIRMED
        success = self._cc_client.addReviewStatusRule(
            bug.bugHash, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, review_comment)
        self.assertEqual(report.reviewData.status, status)

        # There is one system comment for this bug.
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 1)

        # There is only one review status rule in the database.
        rules = self._cc_client.getReviewStatusRules(None, None, None, 0)
        self.assertEqual(len(rules), 1)

        self.assertEqual(rules[0].reportHash, bug.bugHash)
        self.assertEqual(rules[0].reviewData.comment, review_comment)
        self.assertEqual(rules[0].reviewData.status, status)
        self.assertTrue(rules[0].associatedReportCount > 0)

        self.assertEqual(self._cc_client.getReviewStatusRulesCount(None), 1)

        # Try to update the review status again with the same data and check
        # that no new system comment entry will be created.
        success = self._cc_client.addReviewStatusRule(
            bug.bugHash, status, review_comment)
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 1)
        self.assertEqual(self._cc_client.getReviewStatusRulesCount(None), 1)

        # Test that updating only the review status message a new system
        # comment will be created.
        success = self._cc_client.addReviewStatusRule(
            bug.bugHash, status, "test system comment change")
        self.assertTrue(success)
        comments = self.__get_system_comments(bug.reportId)
        self.assertEqual(len(comments), 2)
        self.assertEqual(self._cc_client.getReviewStatusRulesCount(None), 1)

        # Try to change review status back to unreviewed.
        status = ReviewStatus.UNREVIEWED
        success = self._cc_client.addReviewStatusRule(
            bug.bugHash,
            status,
            None)

        self.assertTrue(success)
        logging.debug("Bug review status changed successfully")

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, '')
        self.assertEqual(report.reviewData.status, status)

        # Change review status to false positive.
        review_comment = 'This is not a bug'
        status = ReviewStatus.FALSE_POSITIVE
        success = self._cc_client.addReviewStatusRule(
            bug.bugHash, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, review_comment)
        self.assertEqual(report.reviewData.status, status)

        # Change review status to intentional.
        review_comment = ''
        status = ReviewStatus.INTENTIONAL
        success = self._cc_client.addReviewStatusRule(
            bug.bugHash, status, review_comment)

        self.assertTrue(success)
        logging.debug('Bug review status changed successfully')

        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, review_comment)
        self.assertEqual(report.reviewData.status, status)

        # Make sure that removing a review status rule will change the review
        # status information of a report back to default values.
        self.__remove_all_rules()
        report = self._cc_client.getReport(bug.reportId)
        self.assertEqual(report.reviewData.comment, None)
        self.assertEqual(report.reviewData.author, None)
        self.assertEqual(report.reviewData.date, None)
        self.assertEqual(report.reviewData.status, ReviewStatus.UNREVIEWED)

    def test_review_status_update_from_source_trim(self):
        """
        Test if the review status comments changes in the source code
        are updated at the server when trim path is used.

        The report is store twice and between the storage the
        review status as a source code comment is modified.
        The test checks is after the source code modification
        and storage the review status is updated correctly at
        the server too.
        """
        test_project_path = os.path.join(self.test_workspace,
                                         'review_status_files')
        test_project_name = 'review_status_update_proj'

        plist_file = os.path.join(test_project_path, 'divide_zero.plist')
        source_file = os.path.join(test_project_path, 'divide_zero.cpp')
        plist_test.prefix_file_path(plist_file, test_project_path)

        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg['reportdir'] = test_project_path

        codechecker.store(codechecker_cfg, test_project_name)

        codechecker_cfg['trim_path_prefix'] = test_project_path

        # Run data for the run created by this test case.
        run_filter = RunFilter(names=[test_project_name], exactMatch=True)

        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        run = runs[0]
        runid = run.runId
        logging.debug('Get all run results from the db for runid: ' +
                      str(runid))

        reports = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(reports)
        self.assertNotEqual(len(reports), 0)
        self.assertEqual(len(reports), 2)

        for report in reports:
            print(report)
            self.assertEqual(report.reviewData.status,
                             ReviewStatus.INTENTIONAL)

        # Modify review comments from intentional to confirmed for the
        # second store.
        with open(source_file, 'r+', encoding='utf-8', errors='ignore') as sf:
            content = sf.read()
            new_content = content.replace("codechecker_intentional",
                                          "codechecker_confirmed")
            sf.truncate(0)
            sf.write(new_content)

        # modify review comments and store the reports again
        with open(source_file, encoding='utf-8', errors='ignore') as sf:
            content = sf.read()

        # Update the plist file modification date to be newer than
        # the source file so it can be stored, because there was no
        # actual analysis.
        date = datetime.datetime.now() + datetime.timedelta(minutes=5)
        mod_time = time.mktime(date.timetuple())
        os.utime(plist_file, (mod_time, mod_time))

        codechecker.store(codechecker_cfg, test_project_name)

        # Check if all the review statuses were updated to the new at the
        # server.
        reports = get_all_run_results(self._cc_client, runid)
        self.assertIsNotNone(reports)
        self.assertNotEqual(len(reports), 0)
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report.reviewData.status, ReviewStatus.CONFIRMED)

    def test_filter_review_status_rules(self):
        """ Test filtering review status rules based on different filters. """
        run_results = get_all_run_results(self._cc_client, self._runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug1 = run_results[0]
        bug2 = next(r for r in run_results if r.bugHash != bug1.bugHash)

        success = self._cc_client.addReviewStatusRule(
            bug1.bugHash, ReviewStatus.CONFIRMED, 'bug1')
        self.assertTrue(success)

        success = self._cc_client.addReviewStatusRule(
            bug2.bugHash, ReviewStatus.FALSE_POSITIVE, 'bug2')
        self.assertTrue(success)

        rule_filter = None
        sort_mode = None
        limit = None
        offset = 0

        # There are two rules in the database.
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.assertEqual(len(rules), 2)

        # Show only Confirmed rules.
        rule_filter = ReviewStatusRuleFilter(
            reviewStatuses=[ReviewStatus.CONFIRMED])
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].reviewData.status, ReviewStatus.CONFIRMED)

        self.assertEqual(
            self._cc_client.getReviewStatusRulesCount(rule_filter), 1)

        # Show both Confirmed and False positive rules.
        rule_filter = ReviewStatusRuleFilter(
            reviewStatuses=[
                ReviewStatus.CONFIRMED, ReviewStatus.FALSE_POSITIVE])
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.assertEqual(len(rules), 2)
        self.assertEqual(
            self._cc_client.getReviewStatusRulesCount(rule_filter), 2)

        # Filter by report hash.
        rule_filter = ReviewStatusRuleFilter(reportHashes=[bug1.bugHash])
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].reviewData.status, ReviewStatus.CONFIRMED)

        # Add a review status rule with a non-existing report hash.
        success = self._cc_client.addReviewStatusRule(
            'invalid', ReviewStatus.INTENTIONAL, 'bug3')
        self.assertTrue(success)

        rule_filter = ReviewStatusRuleFilter(noAssociatedReports=True)
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].reviewData.status, ReviewStatus.INTENTIONAL)
        self.assertEqual(rules[0].associatedReportCount, 0)

    def test_sort_review_status_rules(self):
        """ Test sorting review status rules. """
        run_results = get_all_run_results(self._cc_client, self._runid)
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        bug1 = run_results[0]
        bug2 = next(r for r in run_results if r.bugHash != bug1.bugHash)

        success = self._cc_client.addReviewStatusRule(
            bug1.bugHash, ReviewStatus.CONFIRMED, 'bug1')
        self.assertTrue(success)

        success = self._cc_client.addReviewStatusRule(
            bug2.bugHash, ReviewStatus.FALSE_POSITIVE, 'bug2')
        self.assertTrue(success)

        success = self._cc_client.addReviewStatusRule(
            'invalid', ReviewStatus.INTENTIONAL, 'bug3')
        self.assertTrue(success)

        # By default the rules are sorted by the date field in descending
        # order.
        rule_filter = None
        sort_mode = None
        limit = None
        offset = 0
        rules = self._cc_client.getReviewStatusRules(
            rule_filter, sort_mode, limit, offset)
        self.assertEqual(len(rules), 3)

        self.__check_value_order(
            [r.reviewData.date for r in rules], Order.DESC)

        # Test ordering rules by date.
        self.__check_rule_order(
            lambda r: r.reviewData.date, ReviewStatusRuleSortType.DATE)

        # Test ordering rules by report hash.
        self.__check_rule_order(
            lambda r: r.reportHash, ReviewStatusRuleSortType.REPORT_HASH)

        # Test ordering rules by author.
        self.__check_rule_order(
            lambda r: r.reviewData.author, ReviewStatusRuleSortType.AUTHOR)

        # Test ordering rules by review status.
        self.__check_rule_order(
            lambda r: r.reviewData.status, ReviewStatusRuleSortType.STATUS)

        # Test ordering rules by associated report count.
        self.__check_rule_order(
            lambda r: r.associatedReportCount,
            ReviewStatusRuleSortType.ASSOCIATED_REPORTS_COUNT)

    def test_review_status(self):
        """
        Test review status changes
        """
        project.clean('suppress', env.test_env(self.test_workspace))

        suppress_project_bugs = project.get_info('suppress')['bugs']

        codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)
        codechecker_cfg['reportdir'] = os.path.join(
            self.test_workspace, 'suppress_reports')

        test_project_name1 = 'review_status_change1'

        ret = codechecker.check_and_store(
            codechecker_cfg,
            test_project_name1,
            project.path('suppress'))
        self.assertEqual(ret, 0)

        # Check and store "suppress" sample project. The review status data
        # should match the ones in project_info.json.

        run_filter = RunFilter(names=[test_project_name1], exactMatch=True)
        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        runid1 = next(r.runId for r in runs if r.name == test_project_name1)

        reports1 = get_all_run_results(self._cc_client, runid1)

        for report in reports1:
            self.assertIn(
                (report.line,
                 report.reviewData.status,
                 report.reviewData.comment),
                map(lambda x:
                    (x['line'],
                     x['review_status'],
                     x['review_status_comment']),
                    suppress_project_bugs[report.bugHash]))

        # Change the review status of some reports. The one with source code
        # comment shouldn't change and the one without source code comment
        # should.

        NULL_DEREF_BUG_HASH = '0c07579523063acece2d7aebd4357cac'
        UNCOMMENTED_BUG_HASH = 'f0bf9810fe405de502137f1eb71fb706'
        MULTI_REPORT_HASH = '2d019b15c17a7cf6aa3b238b916872ba'

        null_deref_report_id = next(
            r.reportId for r in reports1
            if r.bugHash == NULL_DEREF_BUG_HASH)
        uncommented_report_id = next(
            r.reportId for r in reports1
            if r.bugHash == UNCOMMENTED_BUG_HASH)

        multi_confirmed_id = next(
            r.reportId for r in reports1
            if r.bugHash == MULTI_REPORT_HASH and
            r.reviewData.status == ReviewStatus.CONFIRMED)

        self._cc_client.changeReviewStatus(
            null_deref_report_id,
            ReviewStatus.INTENTIONAL,
            "This is intentional")
        self._cc_client.changeReviewStatus(
            uncommented_report_id,
            ReviewStatus.INTENTIONAL,
            "This is intentional")
        self._cc_client.changeReviewStatus(
            multi_confirmed_id,
            ReviewStatus.FALSE_POSITIVE,
            "This is false positive.")

        reports1 = get_all_run_results(self._cc_client, runid1)

        null_deref_report1 = next(filter(
            lambda r: r.bugHash == NULL_DEREF_BUG_HASH,
            reports1))
        uncommented_report1 = next(filter(
            lambda r: r.bugHash == UNCOMMENTED_BUG_HASH,
            reports1))

        multi_confirmed_report = next(filter(
            lambda r: r.bugHash == MULTI_REPORT_HASH and
            r.reviewData.status == ReviewStatus.CONFIRMED,
            reports1))
        multi_intentional_report = next(filter(
            lambda r: r.bugHash == MULTI_REPORT_HASH and
            r.reviewData.status == ReviewStatus.INTENTIONAL,
            reports1))
        multi_unreviewed_report = next(filter(
            lambda r: r.bugHash == MULTI_REPORT_HASH and
            r.reviewData.status == ReviewStatus.UNREVIEWED,
            reports1), None)
        multi_false_positive_report = next(filter(
            lambda r: r.bugHash == MULTI_REPORT_HASH and
            r.reviewData.status == ReviewStatus.FALSE_POSITIVE,
            reports1))

        self.assertIn(
            (null_deref_report1.reviewData.status,
             null_deref_report1.reviewData.comment),
            map(lambda x:
                (x['review_status'], x['review_status_comment']),
                suppress_project_bugs[null_deref_report1.bugHash]))
        self.assertEqual(
            uncommented_report1.reviewData.status,
            ReviewStatus.INTENTIONAL)
        self.assertEqual(
            uncommented_report1.reviewData.comment,
            "This is intentional")
        self.assertEqual(
            multi_confirmed_report.reviewData.comment,
            "Has a source code comment.")
        self.assertEqual(
            multi_intentional_report.reviewData.comment,
            "Has a different source code comment.")
        # Only the one with no source code comment changes its review status.
        self.assertEqual(
            multi_false_positive_report.reviewData.comment,
            "This is false positive.")
        self.assertIsNone(multi_unreviewed_report)

        # Storing the report directory of the project inserts further reports
        # to the database with the same bug hashes. The review status of
        # reports without source code comment should get the default review
        # status set earlier.

        test_project_name2 = 'review_status_change2'
        codechecker.store(codechecker_cfg, test_project_name2)

        run_filter = RunFilter(names=[test_project_name2], exactMatch=True)
        runs = self._cc_client.getRunData(run_filter, None, 0, None)
        runid2 = next(r.runId for r in runs if r.name == test_project_name2)

        reports2 = get_all_run_results(self._cc_client, runid2)

        uncommented_report2 = next(filter(
            lambda r: r.bugHash == UNCOMMENTED_BUG_HASH,
            reports2))

        self.assertEqual(
            uncommented_report2.reviewData.status,
            ReviewStatus.INTENTIONAL)
        self.assertEqual(
            uncommented_report2.reviewData.comment,
            "This is intentional")
