#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Blame info function test. """


import json
import os
import subprocess
import shutil
import sys
import tempfile
import unittest
import uuid

from codechecker_api.codeCheckerDBAccess_v6.ttypes import Order, \
  ReportFilter, RunFilter, RunSortMode, RunSortType
from libtest.thrift_client_to_db import get_all_run_results

from libtest import codechecker
from libtest import env
from libtest import project


class TestBlameInfo(unittest.TestCase):

    def setup_class(self):
        """Setup the environment for testing blame information."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('blame')

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

        test_project = 'cpp'
        test_config = {}
        project_info = project.get_info(test_project)

        test_project_path = os.path.join(TEST_WORKSPACE, "test_proj")
        shutil.copytree(project.path(test_project), test_project_path)

        project_info['project_path'] = test_project_path
        test_project_name = project_info['name'] + '_' + uuid.uuid4().hex
        test_config['test_project'] = project_info

        suppress_file = None
        skip_list_file = None
        test_env = env.test_env(TEST_WORKSPACE)

        codechecker_cfg = {
            'suppress_file': suppress_file,
            'skip_list_file': skip_list_file,
            'check_env': test_env,
            'workspace': TEST_WORKSPACE,
            'checkers': [],
            'clean': True
        }

        # Start or connect to the running CodeChecker server and get connection
        # details.
        print("This test uses a CodeChecker server... connecting...")
        server_access = codechecker.start_or_get_server(auth_required=True)
        server_access['viewer_product'] = 'blame'
        codechecker.add_test_package_product(server_access, TEST_WORKSPACE)

        # Extend the checker configuration with the server access.
        codechecker_cfg.update(server_access)

        # Clean the test project, if needed by the tests.
        ret = project.clean(test_project)
        if ret:
            sys.exit(ret)

        ret = codechecker.check_and_store(
          codechecker_cfg, test_project_name, project.path(test_project))
        if ret:
            sys.exit(1)
        print("Analyzing test project was succcessful.")

        # Save the run names in the configuration.
        codechecker_cfg['run_names'] = [test_project_name]

        test_config['codechecker_cfg'] = codechecker_cfg

        # Export the test configuration to the workspace.
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
        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        self._codechecker_cfg = env.import_codechecker_cfg(self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._test_dir = os.path.join(self.test_workspace, 'test_files')
        self._run_name = 'hello'

        try:
            os.makedirs(self._test_dir)
        except os.error:
            # Directory already exists.
            pass

        # Setup a viewer client to test viewer API calls.
        self._cc_client = env.setup_viewer_client(self.test_workspace)
        self.assertIsNotNone(self._cc_client)

        sort_mode = RunSortMode(RunSortType.DATE, Order.ASC)
        self.test_runs = self._cc_client.getRunData(None, None, 0, sort_mode)

    def test_update_blame_info(self):
        with tempfile.TemporaryDirectory() as proj_dir:
            source_file_name = "update_blame.cpp"
            src_file = os.path.join(proj_dir, source_file_name)

            with open(os.path.join(proj_dir, 'Makefile'), 'w',
                      encoding="utf-8", errors="ignore") as f:
                f.write(f"all:\n\t$(CXX) -c {src_file} -o /dev/null")

            with open(os.path.join(proj_dir, 'project_info.json'), 'w',
                      encoding="utf-8", errors="ignore") as f:
                json.dump({
                    "name": "update_blame",
                    "clean_cmd": "",
                    "build_cmd": "make"}, f)

            with open(src_file, 'w', encoding="utf-8", errors="ignore") as f:
                f.write("int main() { sizeof(42); }")

            # Change working dir to testfile dir so CodeChecker can be run
            # easily.
            old_pwd = os.getcwd()
            os.chdir(proj_dir)

            run_name = "update_blame_info"
            codechecker.check_and_store(
                self._codechecker_cfg, run_name, proj_dir)

            run_filter = RunFilter(names=[run_name], exactMatch=True)
            runs = self._cc_client.getRunData(run_filter, None, 0, None)
            run_id = runs[0].runId

            report_filter = ReportFilter(
                checkerName=['*'],
                filepath=[f'*{source_file_name}'])

            run_results = get_all_run_results(
                self._cc_client, run_id, [], report_filter)
            self.assertIsNotNone(run_results)

            report = run_results[0]

            # Get source file data.
            file_data = self._cc_client.getSourceFileData(
                report.fileId, True, None)
            self.assertIsNotNone(file_data)
            self.assertFalse(file_data.hasBlameInfo)
            self.assertFalse(file_data.remoteUrl)
            self.assertFalse(file_data.trackingBranch)

            # Get blame information
            blame_info = self._cc_client.getBlameInfo(report.fileId)
            self.assertIsNotNone(blame_info)
            self.assertFalse(blame_info.commits)
            self.assertFalse(blame_info.blame)

            # Create a .git structure that is as bare as possible, without
            # getting interference from the user's configuration.
            subprocess.Popen(['git', 'init', proj_dir,
                              "--template", "/usr/share/git-core/templates"
                              ]).communicate()

            subprocess.Popen([
                'git',
                'remote',
                'add',
                'origin',
                'https://myurl.com']).communicate()
            subprocess.Popen(['git', 'add', src_file]).communicate()
            subprocess.Popen([
                'git',
                '-c', 'user.name=hello',
                '-c', 'user.email=world',
                'commit',
                '--no-verify',
                '--message', 'message']).communicate()

            codechecker.store(self._codechecker_cfg, run_name)

            os.chdir(old_pwd)

            # Get source file data.
            file_data = self._cc_client.getSourceFileData(
                report.fileId, True, None)
            self.assertIsNotNone(file_data)
            self.assertTrue(file_data.hasBlameInfo)
            self.assertTrue(file_data.remoteUrl)
            self.assertTrue(file_data.trackingBranch)

            # Get blame information
            blame_info = self._cc_client.getBlameInfo(report.fileId)
            self.assertIsNotNone(blame_info)
            self.assertTrue(blame_info.commits)
            self.assertTrue(blame_info.blame)

    def test_no_blame_info(self):
        """ Test if the source file doesn't have any blame information. """
        with tempfile.TemporaryDirectory() as proj_dir:
            source_file_name = "no_blame.cpp"
            src_file = os.path.join(proj_dir, source_file_name)

            with open(os.path.join(proj_dir, 'Makefile'), 'w',
                      encoding="utf-8", errors="ignore") as f:
                f.write(f"all:\n\t$(CXX) -c {src_file} -o /dev/null\n")

            with open(os.path.join(proj_dir, 'project_info.json'), 'w',
                      encoding="utf-8", errors="ignore") as f:
                json.dump({
                    "name": "hello",
                    "clean_cmd": "",
                    "build_cmd": "make"}, f)

            with open(src_file, 'w', encoding="utf-8", errors="ignore") as f:
                f.write("int main() { sizeof(42); }")

            # Change working dir to testfile dir so CodeChecker can be run
            # easily.
            old_pwd = os.getcwd()
            os.chdir(proj_dir)

            run_name = "no_blame_info"
            codechecker.check_and_store(
                self._codechecker_cfg, run_name, proj_dir)

            os.chdir(old_pwd)

            run_filter = RunFilter(names=[run_name], exactMatch=True)
            runs = self._cc_client.getRunData(run_filter, None, 0, None)
            run_id = runs[0].runId

            report_filter = ReportFilter(
                checkerName=['*'],
                filepath=[f'*{source_file_name}'])

            run_results = get_all_run_results(
                self._cc_client, run_id, [], report_filter)
            self.assertIsNotNone(run_results)

            report = run_results[0]

            # Get source file data.
            file_data = self._cc_client.getSourceFileData(
                report.fileId, True, None)
            self.assertIsNotNone(file_data)
            self.assertFalse(file_data.hasBlameInfo)
            self.assertFalse(file_data.remoteUrl)
            self.assertFalse(file_data.trackingBranch)

            # Get blame information
            blame_info = self._cc_client.getBlameInfo(report.fileId)
            self.assertIsNotNone(blame_info)
            self.assertFalse(blame_info.commits)
            self.assertFalse(blame_info.blame)

    def test_get_blame_info(self):
        """ Get blame information for a source file. """
        runid = self.test_runs[0].runId
        report_filter = ReportFilter(
            checkerName=['*'],
            filepath=['*call_and_message.cpp*'])

        run_results = get_all_run_results(
            self._cc_client, runid, [], report_filter)
        self.assertIsNotNone(run_results)

        report = run_results[0]

        # Get source file data.
        file_data = self._cc_client.getSourceFileData(
            report.fileId, True, None)
        self.assertIsNotNone(file_data)
        self.assertTrue(file_data.hasBlameInfo)
        self.assertTrue(file_data.remoteUrl)
        self.assertTrue(file_data.trackingBranch)

        # Get blame information
        blame_info = self._cc_client.getBlameInfo(report.fileId)
        self.assertIsNotNone(blame_info)
        self.assertTrue(len(blame_info.commits))
        self.assertTrue(len(blame_info.blame))
