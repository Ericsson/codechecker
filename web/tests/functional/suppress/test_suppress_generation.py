# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Test source-code level suppression data writing to suppress file.
"""


import logging
import os
import shlex
import shutil
import subprocess
import sys
from subprocess import CalledProcessError
import unittest
import uuid

from codechecker_api.codeCheckerDBAccess_v6.ttypes import ReviewStatus

from libtest import codechecker
from libtest import env
from libtest import project
from libtest.thrift_client_to_db import get_all_run_results


def _generate_suppress_file(suppress_file):
    """
    Create a dummy suppress file just to check if the old and the new
    suppress format can be processed.
    """
    print("Generating suppress file: " + suppress_file)

    import calendar
    import hashlib
    import random
    import time

    hash_version = '1'
    suppress_stuff = []
    for _ in range(10):
        curr_time = calendar.timegm(time.gmtime())
        random_integer = random.randint(1, 9999999)
        suppress_line = str(curr_time) + str(random_integer)
        suppress_stuff.append(
            hashlib.md5(
                suppress_line.encode('utf-8')).hexdigest() +
            '#' + hash_version)

    s_file = open(suppress_file, 'w', encoding="utf-8", errors="ignore")
    for k in suppress_stuff:
        s_file.write(k + '||' + 'idziei éléáálk ~!@#$#%^&*() \n')
        s_file.write(
            k + '||' + 'test_~!@#$%^&*.cpp' +
            '||' + 'idziei éléáálk ~!@#$%^&*(\n')
        s_file.write(
            hashlib.md5(suppress_line.encode('utf-8')).hexdigest() + '||' +
            'test_~!@#$%^&*.cpp' + '||' + 'idziei éléáálk ~!@#$%^&*(\n')

    s_file.close()


def call_cmd(command, cwd, env):
    try:
        print(' '.join(command))
        proc = subprocess.Popen(
            shlex.split(' '.join(command)),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env, encoding="utf-8", errors="ignore")
        out, err = proc.communicate()
        print(out)
        print(err)
        return proc.returncode
    except CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


class TestSuppress(unittest.TestCase):
    """
    Test source-code level suppression data writing to suppress file.
    """

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('suppress')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_project = 'suppress'

        test_config = {}

        project_info = project.get_info(test_project)

        test_proj_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_proj_path)

        project_info['project_path'] = test_proj_path

        test_config['test_project'] = project_info

        # Generate a suppress file for the tests.
        suppress_file = os.path.join(TEST_WORKSPACE, 'suppress_file')
        if os.path.isfile(suppress_file):
            os.remove(suppress_file)
        _generate_suppress_file(suppress_file)

        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'suppress_file': None,
            'skip_list_file': None,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'analyzers': ['clangsa', 'clang-tidy']
        }

        ret = project.clean(test_project, test_env)
        if ret:
            sys.exit(ret)

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server()
        server_access['viewer_product'] = 'suppress'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex

        ret = codechecker.check_and_store(codechecker_cfg,
                                          test_project_name,
                                          project.path(test_project))

        if ret:
            sys.exit(1)
        print("Analyzing the test project was successful.")
        test_project_name_dup = test_project_name + "_duplicate"
        ret = codechecker.store(codechecker_cfg, test_project_name_dup)

        codechecker_cfg['run_names'] = [test_project_name,
                                        test_project_name_dup]
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

    def setup_method(self, method):
        self._test_workspace = os.environ['TEST_WORKSPACE']

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._test_project_path = self._testproject_data['project_path']

        self._cc_client = env.setup_viewer_client(self._test_workspace)
        self.assertIsNotNone(self._cc_client)

        # Get the run names which belong to this test
        run_names = env.get_run_names(self._test_workspace)

        runs = self._cc_client.getRunData(None, None, 0, None)

        test_runs = [run for run in runs if run.name in run_names]

        self.assertEqual(len(test_runs), 2,
                         'There should 2 runs for this test.')
        self._runid = test_runs[0].runId
        self._run_name = test_runs[0].name

        self._runid_dup = test_runs[1].runId
        self._run_name_dup = test_runs[1].name

        self._test_directory = os.path.dirname(os.path.realpath(__file__))

    def test_suppress_import(self):
        """
        Test the suppress file importing.
        """
        logging.info("testing suppress import")

        generated_file = os.path.join(self._test_workspace,
                                      "generated.suppress")

        extract_cmd = ['CodeChecker', 'parse',
                       os.path.join(self._test_workspace, "reports"),
                       "--suppress", generated_file,
                       "--export-source-suppress"
                       ]

        ret = call_cmd(extract_cmd,
                       self._test_project_path,
                       env.test_env(self._test_workspace))
        self.assertEqual(ret, 2, "Failed to generate suppress file.")

        codechecker_cfg = env.import_test_cfg(
            self._test_workspace)['codechecker_cfg']

        product_url = env.parts_to_url(codechecker_cfg)
        import_cmd = ['CodeChecker', 'cmd', 'suppress', '-i', generated_file,
                      '--url', product_url, self._run_name]

        print(import_cmd)
        ret = call_cmd(import_cmd,
                       self._test_project_path,
                       env.test_env(self._test_workspace))
        self.assertEqual(ret, 0, "Failed to import suppress file.")

    def test_suppress_comment_in_db(self):
        """
        Exported source suppress comment stored as a review status in the db.
        """
        runid = self._runid
        logging.debug("Get all run results from the db for runid: " +
                      str(runid))

        expected_file_path = os.path.join(self._test_directory,
                                          "suppress.expected")

        hash_to_suppress_msgs = {}
        with open(expected_file_path, 'r', encoding="utf-8",
                  errors="ignore") as expected_file:
            for line in expected_file:
                src_code_info = line.strip().split('||')

                status = None
                if len(src_code_info) == 4:
                    # Newest source code comment format where status is given.
                    bug_hash, _, msg, status = src_code_info
                elif len(src_code_info) == 3:
                    # Old format where review status is not given.
                    bug_hash, _, msg = src_code_info
                else:
                    # Oldest source code comment format where status and file
                    # name are not given.
                    bug_hash, msg = src_code_info

                rw_status = ReviewStatus.FALSE_POSITIVE
                if status == 'confirmed':
                    rw_status = ReviewStatus.CONFIRMED
                elif status == 'intentional':
                    rw_status = ReviewStatus.INTENTIONAL

                hash_to_suppress_msgs[bug_hash] = {'message': msg,
                                                   'status': rw_status}

        run_results = get_all_run_results(self._cc_client, runid)
        logging.debug("Run results:")
        [logging.debug(x) for x in run_results]
        self.assertIsNotNone(run_results)
        self.assertNotEqual(len(run_results), 0)

        for bug_hash in hash_to_suppress_msgs:
            logging.debug("tesing for bug hash " + bug_hash)
            expected_data = hash_to_suppress_msgs[bug_hash]
            report_data_of_bug = [
                report_data for report_data in run_results
                if report_data.bugHash == bug_hash]
            self.assertEqual(len(report_data_of_bug), 1)
            report_data = report_data_of_bug[0]

            # Check the stored suppress comment
            self.assertEqual(report_data.reviewData.comment,
                             expected_data['message'])
            self.assertEqual(report_data.reviewData.status,
                             expected_data['status'])

            # Even review status with source code comment can change.
            review_comment = "This is really a bug"
            status = ReviewStatus.CONFIRMED
            success = self._cc_client.changeReviewStatus(
                report_data.reportId, status, review_comment)

            self.assertTrue(success)

        # Review status without source code comment can change.
        uncommented_report = next(filter(
            lambda r: r.reviewData.status == ReviewStatus.UNREVIEWED,
            iter(run_results)))
        self._cc_client.changeReviewStatus(
            uncommented_report.reportId,
            ReviewStatus.CONFIRMED,
            'This is a known issue')

        # Get the results to compare from the primary run
        updated_results = get_all_run_results(self._cc_client, self._runid)
        # Get the results from the duplicated run
        updated_results_dup = \
            get_all_run_results(self._cc_client, self._runid_dup)
        hash_to_report_updated = {r.bugHash: r for r in updated_results}
        self.assertIsNotNone(updated_results)
        self.assertNotEqual(len(updated_results), 0)

        # Review status of reports with source code comment can change
        # as they are stored as individual comments
        for bug_hash in hash_to_suppress_msgs:
            self.assertEqual(
                ReviewStatus.CONFIRMED,
                hash_to_report_updated[bug_hash].reviewData.status)
            self.assertEqual(
                "This is really a bug",
                hash_to_report_updated[bug_hash].reviewData.comment)

        # Review status of reports without source code comment changes.
        uncommented_report_updated = next(filter(
            lambda r: r.bugHash == uncommented_report.bugHash,
            iter(updated_results)))

        self.assertEqual(
            uncommented_report_updated.reviewData.status,
            ReviewStatus.CONFIRMED)
        self.assertEqual(
            uncommented_report_updated.reviewData.comment,
            'This is a known issue')

        # Review status of the same report in the duplicate run must not change
        uncommented_report_updated_dup = next(filter(
            lambda r: r.bugHash == uncommented_report.bugHash,
            iter(updated_results_dup)))

        self.assertEqual(
            uncommented_report_updated_dup.reviewData.status,
            ReviewStatus.UNREVIEWED)

        # Check the same project again.
        codechecker_cfg = env.import_test_cfg(
            self._test_workspace)['codechecker_cfg']

        initial_test_project_name = self._run_name

        ret = codechecker.check_and_store(codechecker_cfg,
                                          initial_test_project_name,
                                          self._test_project_path)
        self.assertEqual(0, ret, "Could not store test data to the server.")

        # Get the results to compare.
        updated_results = get_all_run_results(self._cc_client, self._runid)
        self.assertIsNotNone(updated_results)
        self.assertNotEqual(len(updated_results), 0)

        for bug_hash in hash_to_suppress_msgs:
            expected_data = hash_to_suppress_msgs[bug_hash]
            report_data = [report_data for report_data in updated_results
                           if report_data.bugHash == bug_hash][0]

            # Check that source code comments in the database are changed back
            # after storage.
            self.assertEqual(report_data.reviewData.comment,
                             expected_data['message'])
            self.assertEqual(report_data.reviewData.status,
                             expected_data['status'])
