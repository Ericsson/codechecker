#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
""" CTU function test."""

import json
import os
import shutil
import unittest
import zipfile

from libtest import env
from libtest import project
from libtest.codechecker import call_command

from libcodechecker.analyze import host_check

NO_CTU_MESSAGE = "CTU is not supported"
NO_DISPLAY_CTU_PROGRESS = "-analyzer-display-ctu-progress is not supported"


class TestCtu(unittest.TestCase):
    """ Test CTU functionality. """

    def setUp(self):
        """ Set up workspace."""

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self.env = env.codechecker_env()
        self.report_dir = os.path.join(self.test_workspace, 'reports')
        os.makedirs(self.report_dir)

    def __set_up_test_dir(self, project_path):
        self.test_dir = project.path(project_path)

        # Get if clang is CTU-capable or not.
        cmd = [self._codechecker_cmd, 'analyze', '-h']
        output, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        self.ctu_capable = '--ctu-' in output
        print("'analyze' reported CTU-compatibility? " + str(self.ctu_capable))

        self.ctu_has_analyzer_display_ctu_progress = \
            host_check.has_analyzer_feature(self.__getClangSaPath(),
                                            '-analyzer-display-ctu-progress')
        print("Has -analyzer-display-ctu-progress? " + str(self.ctu_capable))

        # Fix the "template" build JSONs to contain a proper directory
        # so the tests work.
        raw_buildlog = os.path.join(self.test_dir, 'buildlog.json')
        with open(raw_buildlog) as log_file:
            build_json = json.load(log_file)
            for command in build_json:
                command['directory'] = self.test_dir

        os.chdir(self.test_workspace)
        self.buildlog = os.path.join(self.test_workspace, 'buildlog.json')
        with open(self.buildlog, 'w') as log_file:
            json.dump(build_json, log_file)

    def tearDown(self):
        """ Tear down workspace."""

        shutil.rmtree(self.report_dir, ignore_errors=True)

    def test_ctu_logs_ast_import(self):
        """ Test that Clang indeed logs the AST import events.
        """
        self.__set_up_test_dir('ctu_failure')
        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        if not self.ctu_has_analyzer_display_ctu_progress:
            self.skipTest(NO_DISPLAY_CTU_PROGRESS)

        output = self.__do_ctu_all(reparse=False,
                                   extra_args=["--verbose", "debug"])
        self.assertIn("ANALYZE (CTU loaded AST for source file)", output)

    def test_ctu_failure_zip(self):
        """ Test the failure zip contains the source of imported TU
        """
        self.__set_up_test_dir('ctu_failure')
        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        if not self.ctu_has_analyzer_display_ctu_progress:
            self.skipTest(NO_DISPLAY_CTU_PROGRESS)

        # The below special checker `ExprInspection` crashes when a function
        # with a specified name is analyzed.
        output = self.__do_ctu_all(reparse=False,
                                   extra_args=[
                                       "--verbose", "debug",
                                       "-e", "debug.ExprInspection"
                                   ])

        # lib.c should be logged as its AST is loaded by Clang
        self.assertRegexpMatches(
                output,
                "ANALYZE \(CTU loaded AST for source file\): .*lib\.c")

        # We expect a failure archive to be in the failed directory.
        failed_dir = os.path.join(self.report_dir, "failed")
        failed_files = os.listdir(failed_dir)
        self.assertEquals(len(failed_files), 1)
        # Ctu should fail during analysis of main.c
        self.assertIn("main.c", failed_files[0])

        fail_zip = os.path.join(failed_dir, failed_files[0])

        with zipfile.ZipFile(fail_zip, 'r') as archive:
            files = archive.namelist()

            self.assertIn("build-action", files)
            self.assertIn("analyzer-command", files)

            def check_source_in_archive(source_in_archive):
                source_file = os.path.join(self.test_dir, source_in_archive)
                source_in_archive = os.path.join("sources-root",
                                                 source_file.lstrip('/'))
                self.assertIn(source_in_archive, files)
                # Check file content.
                with archive.open(source_in_archive, 'r') as archived_code:
                    with open(source_file, 'r') as source_code:
                        self.assertEqual(archived_code.read(),
                                         source_code.read())

            check_source_in_archive("main.c")
            check_source_in_archive("lib.c")

    def test_ctu_failure_zip_with_headers(self):
        """
        Test the failure zip contains the source of imported TU and all the
        headers on which the TU depends.
        """
        self.__set_up_test_dir('ctu_failure_with_headers')
        if not self.ctu_capable:
            self.skipTest(NO_CTU_MESSAGE)
        if not self.ctu_has_analyzer_display_ctu_progress:
            self.skipTest(NO_DISPLAY_CTU_PROGRESS)

        # The below special checker `ExprInspection` crashes when a function
        # with a specified name is analyzed.
        output = self.__do_ctu_all(reparse=False,
                                   extra_args=[
                                       "--verbose", "debug",
                                       "-e", "debug.ExprInspection"
                                   ])

        # lib.c should be logged as its AST is loaded by Clang
        self.assertRegexpMatches(
                output,
                "ANALYZE \(CTU loaded AST for source file\): .*lib\.c")

        # We expect a failure archive to be in the failed directory.
        failed_dir = os.path.join(self.report_dir, "failed")
        failed_files = os.listdir(failed_dir)
        self.assertEquals(len(failed_files), 1)
        # Ctu should fail during analysis of main.c
        self.assertIn("main.c", failed_files[0])

        fail_zip = os.path.join(failed_dir, failed_files[0])

        with zipfile.ZipFile(fail_zip, 'r') as archive:
            files = archive.namelist()

            self.assertIn("build-action", files)
            self.assertIn("analyzer-command", files)

            def check_source_in_archive(source_in_archive):
                source_file = os.path.join(self.test_dir, source_in_archive)
                source_in_archive = os.path.join("sources-root",
                                                 source_file.lstrip('/'))
                self.assertIn(source_in_archive, files)
                # Check file content.
                with archive.open(source_in_archive, 'r') as archived_code:
                    with open(source_file, 'r') as source_code:
                        self.assertEqual(archived_code.read(),
                                         source_code.read())

            check_source_in_archive("main.c")
            check_source_in_archive("lib.c")
            check_source_in_archive("lib.h")

    def __do_ctu_all(self, reparse, extra_args=None):
        """
        Execute a full CTU run.
        @param extra_args: list of additional arguments
        """

        cmd = [self._codechecker_cmd, 'analyze', '-o', self.report_dir,
               '--analyzers', 'clangsa', '--ctu-all']
        if reparse:
            cmd.append('--ctu-on-the-fly')
        if extra_args is not None:
            cmd.extend(extra_args)
        cmd.append(self.buildlog)

        out, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        return out

    def __getClangSaPath(self):
        cmd = [self._codechecker_cmd, 'analyzers', '--details', '-o', 'json']
        output, _ = call_command(cmd, cwd=self.test_dir, env=self.env)
        json_data = json.loads(output)
        if json_data[0]["name"] == "clangsa":
            return json_data[0]["path"]
        if json_data[1]["name"] == "clangsa":
            return json_data[1]["path"]
