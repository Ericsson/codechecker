#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Test case for the CodeChecker analyze command's direct functionality.
"""

import json
import os
import unittest
import subprocess
import zipfile

from libtest import env


class TestAnalyze(unittest.TestCase):

    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')
        # Change working dir to testfile dir so CodeChecker can be run easily.
        self.__old_pwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)

    def test_capture_analysis_output(self):
        """
        Test if reports/success/<output_file>.[stdout,stderr].txt
        files are created
        """
        build_json = os.path.join(self.test_workspace, "build_success.json")
        success_dir = os.path.join(self.report_dir, "success")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "--capture-analysis-output"]

        source_file = os.path.join(self.test_dir, "success.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
                    analyze_cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, cwd=self.test_dir)
        out, err = process.communicate()
        print(out+err)
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect the sucess stderr file in the success directory.
        success_files = os.listdir(success_dir)
        print(success_files)
        self.assertEquals(len(success_files), 1)
        self.assertIn("success.c", success_files[0])
        os.remove(os.path.join(success_dir, success_files[0]))

    def test_failure(self):
        """
        Test if reports/failed/<failed_file>.zip file is created
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        failed_dir = os.path.join(self.report_dir, "failed")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir]

        source_file = os.path.join(self.test_dir, "failure.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        out, err = process.communicate()
        print(out+err)
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect a failure archive to be in the failed directory.
        failed_files = os.listdir(failed_dir)
        print(failed_files)
        self.assertEquals(len(failed_files), 1)
        self.assertIn("failure.c", failed_files[0])

        fail_zip = os.path.join(failed_dir, failed_files[0])

        with zipfile.ZipFile(fail_zip, 'r') as archive:
            files = archive.namelist()

            self.assertIn("build-action", files)
            self.assertIn("analyzer-command", files)

            with archive.open("build-action", 'r') as archived_buildcmd:
                self.assertEqual(archived_buildcmd.read(),
                                 "gcc -c " + source_file)

            source_in_archive = os.path.join("sources-root",
                                             source_file.lstrip('/'))
            self.assertIn(source_in_archive, files)

            with archive.open(source_in_archive, 'r') as archived_code:
                with open(source_file, 'r') as source_code:
                    self.assertEqual(archived_code.read(), source_code.read())

        os.remove(os.path.join(failed_dir, failed_files[0]))

    def test_robustness_for_dependencygen_failure(self):
        """
        Test if failure ZIP is created even if the dependency generator creates
        an invalid output.
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        failed_dir = os.path.join(self.report_dir, "failed")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir]

        source_file = os.path.join(self.test_dir, "failure.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "cc -c -std=c++11 " + source_file,
                      "file": source_file
                      }]

        # cc -std=c++11 writes error "-std=c++11 valid for C++ but not for C"
        # to its output when invoked as a dependency generator for this
        # build command.

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
                    analyze_cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, cwd=self.test_dir)
        out, err = process.communicate()
        print(out+err)
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect a failure archive to be in the failed directory.
        failed_files = os.listdir(failed_dir)
        print(failed_files)
        self.assertEquals(len(failed_files), 1)
        self.assertIn("failure.c", failed_files[0])

        os.remove(os.path.join(failed_dir, failed_files[0]))
