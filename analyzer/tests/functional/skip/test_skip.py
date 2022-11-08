#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test skipping the analysis of a file and the removal
of skipped reports from the report files.
"""

import glob
import json
import os
import plistlib
import shlex
import subprocess
import tempfile
import unittest

from libtest import env


class TestSkip(unittest.TestCase):
    _ccClient = None

    def setUp(self):

        # TEST_WORKSPACE is automatically set by test package __init__.py .
        self.test_workspace = os.environ['TEST_WORKSPACE']

        test_class = self.__class__.__name__
        print('Running ' + test_class + ' tests in ' + self.test_workspace)

        # Get the CodeChecker cmd if needed for the tests.
        self._codechecker_cmd = env.codechecker_cmd()
        self._tu_collector_cmd = env.tu_collector_cmd()
        self.report_dir = os.path.join(self.test_workspace, "reports")
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files')

    def __analyze_simple(self, build_json, analyzer_extra_options=None):
        """ Analyze the 'simple' project. """
        test_dir = os.path.join(self.test_dir, "simple")
        analyze_cmd = [
            self._codechecker_cmd, "analyze", "-c", build_json,
            "--analyzers", "clangsa", "-o", self.report_dir]

        if analyzer_extra_options:
            analyze_cmd.extend(analyzer_extra_options)

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)
        self.assertEqual(process.returncode, 0)
        return out, err

    def __log_and_analyze_simple(self, analyzer_extra_options=None):
        """ Log and analyze the 'simple' project. """
        test_dir = os.path.join(self.test_dir, "simple")
        build_json = os.path.join(self.test_workspace, "build.json")

        clean_cmd = ["make", "clean"]
        out = subprocess.check_output(clean_cmd,
                                      cwd=test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)

        # Create and run log command.
        log_cmd = [self._codechecker_cmd, "log", "-b", "make",
                   "-o", build_json]
        out = subprocess.check_output(log_cmd,
                                      cwd=test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)
        # Create and run analyze command.
        return self.__analyze_simple(build_json, analyzer_extra_options)

    def __run_parse(self, extra_options=None):
        """ Run parse command with the given extra options. """
        cmd = [
            self._codechecker_cmd, "parse", self.report_dir,
            "--export", "json"]

        if extra_options:
            cmd.extend(extra_options)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        return out, err, process.returncode

    def test_skip(self):
        """Analyze a project with a skip file."""
        self.__log_and_analyze_simple(["--ignore", "skipfile"])

        # Check if file is skipped.
        report_dir_files = os.listdir(self.report_dir)
        for f in report_dir_files:
            self.assertFalse("file_to_be_skipped.cpp" in f)

        # Check if report from the report file is removed.
        report_dir_files = os.listdir(self.report_dir)
        report_file_to_check = None
        for f in report_dir_files:
            if "skip_header.cpp" in f:
                report_file_to_check = os.path.join(self.report_dir, f)
                break

        self.assertIsNotNone(report_file_to_check,
                             "Report file should be generated.")
        report_data = {}
        with open(report_file_to_check, 'rb') as plist_file:
            report_data = plistlib.load(plist_file)
        files = report_data['files']

        skiped_file_index = None
        for i, f in enumerate(files):
            if "skip.h" in f:
                skiped_file_index = i
                break

        for diag in report_data['diagnostics']:
            self.assertNotEqual(diag['location']['file'],
                                skiped_file_index,
                                "Found a location which points to "
                                "skiped file, this report should "
                                "have been removed.")

    def test_analyze_only_header(self):
        """ Analyze source file which depends on a header file. """
        test_dir = os.path.join(self.test_dir, "multiple")
        build_json = os.path.join(self.test_workspace, "build.json")

        # Create and run log command.
        log_cmd = [self._codechecker_cmd, "log", "-b", "make",
                   "-o", build_json]
        out = subprocess.check_output(log_cmd,
                                      cwd=test_dir,
                                      encoding="utf-8", errors="ignore")
        print(out)

        # Use tu_collector to get source file dependencies for a header file
        # and create a skip file from it.
        deps_cmd = [self._tu_collector_cmd, "-l", build_json,
                    "--dependents", "--filter", "*/lib.h"]

        try:
            output = subprocess.check_output(
                deps_cmd,
                cwd=test_dir,
                encoding="utf-8",
                errors="ignore")

            source_files = output.splitlines()
        except subprocess.CalledProcessError as cerr:
            print("Failed to run: " + ' '.join(cerr.cmd))
            print(cerr.output)

        skip_file = os.path.join(self.test_workspace, "skipfile")
        with open(skip_file, 'w', encoding="utf-8", errors="ignore") as skip_f:
            # Include all source file dependencies.
            skip_f.write("\n".join(["+" + s for s in source_files]))

            # Skip all other files.
            skip_f.write("-*")

        analyze_cmd = [self._codechecker_cmd, "analyze", "-c", build_json,
                       "--analyzers", "clangsa",
                       "--ignore", skip_file,
                       "-o", self.report_dir]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)
        errcode = process.returncode
        self.assertEqual(errcode, 0)

        # Check if file is skipped.
        report_dir_files = os.listdir(self.report_dir)

        # Check that we analyzed all source files which depend on the header
        # file.
        self.assertTrue(any(["a.cpp" in f
                             for f in report_dir_files]))
        self.assertTrue(any(["b.cpp" in f
                             for f in report_dir_files]))

        # Get reports only from the header file.
        out, _, _ = self.__run_parse(["--file", "*/lib.h"])

        data = json.loads(out)
        self.assertTrue(len(data['reports']))

    def test_analyze_skip_everything(self):
        """
        Test analyze command when everything is skipped by a skipfile.
        """
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix="skipfile",
                encoding='utf-8') as skip_file:
            # Skip everything by the skip file.
            skip_file.write('-*')
            skip_file.flush()

            self.__log_and_analyze_simple([
                "--ignore", skip_file.name])
            self.assertFalse(
                glob.glob(os.path.join(self.report_dir, '*.plist')))

    def test_analyze_header_with_file_option(self):
        """ Analyze a header file with the --file option. """
        header_file = os.path.join(self.test_dir, "simple", "skip.h")
        out, _ = self.__log_and_analyze_simple(["--file", header_file])
        self.assertIn(
            f"Get dependent source files for '{header_file}'...", out)
        self.assertIn(
            f"Get dependent source files for '{header_file}' done.", out)

        plist_files = glob.glob(os.path.join(self.report_dir, '*.plist'))
        self.assertTrue(plist_files)
        self.assertTrue(all('skip_header.cpp' in f for f in plist_files))

    def test_analyze_header_with_file_option_and_intercept_json(self):
        """
        Analyze a header file with the --file option and a compilation database
        produced by intercept build.
        """
        build_json = os.path.join(self.test_workspace, "build.json")

        # We used to crash when the build log contained 'arguments' fields in
        # place of 'command'. Test that we don't crash on it anymore by
        # manually changing 'command' to 'arguments' here.
        with open(build_json) as f:
            build_actions = json.load(f)
            for ba in build_actions:
                ba['arguments'] = shlex.split(ba['command'])
                del ba['command']

        build_json = os.path.join(self.test_workspace, "build_intercept.json")

        with open(build_json, 'w') as f:
            json.dump(build_actions, f)

        header_file = os.path.join(self.test_dir, "simple", "skip.h")
        out, _ = self.__analyze_simple(build_json, ["--file", header_file])
        self.assertIn(
            f"Get dependent source files for '{header_file}'...", out)
        self.assertIn(
            f"Get dependent source files for '{header_file}' done.", out)

        plist_files = glob.glob(os.path.join(self.report_dir, '*.plist'))
        self.assertTrue(plist_files)
        self.assertTrue(all('skip_header.cpp' in f for f in plist_files))

    def test_analyze_file_option_skip_everything(self):
        """
        Test analyze command --file option when everything is skipped by a
        skipfile.
        """
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix="skipfile",
                encoding='utf-8') as skip_file:
            # Skip everything by the skip file.
            skip_file.write('-*')
            skip_file.flush()

            self.__log_and_analyze_simple([
                "--ignore", skip_file.name,
                "--file", "*/file_to_be_skipped.cpp"])
            self.assertFalse(
                glob.glob(os.path.join(self.report_dir, '*.plist')))

    def test_analyze_file_option(self):
        """
        Test analyze command --file option when everything is skipped except
        a single file.
        """
        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix="skipfile",
                encoding='utf-8') as skip_file:
            # Skip everything except a single source file which is marked as
            # included in the skip file and will be filtered by the --file
            # option.
            skip_file.write('\n'.join([
                '+*skip_header.cpp',
                '-*'
            ]))
            skip_file.flush()

            self.__log_and_analyze_simple([
                "--ignore", skip_file.name,
                "--file", "*/skip_header.cpp"])
            print(glob.glob(
                    os.path.join(self.report_dir, '*.plist')))
            self.assertFalse(
                any('skip_header.cpp' not in f for f in glob.glob(
                    os.path.join(self.report_dir, '*.plist'))))

            # Skip every source files except a single one which will be
            # filtered by the --file option.
            skip_file.write('\n'.join([
                '-*file_to_be_skipped.cpp',
                '-*skip.h'
            ]))
            skip_file.flush()

            self.__log_and_analyze_simple([
                "--ignore", skip_file.name,
                "--file", "*/skip_header.cpp"])
            print(glob.glob(
                    os.path.join(self.report_dir, '*.plist')))
            self.assertFalse(
                any('skip_header.cpp' not in f for f in glob.glob(
                    os.path.join(self.report_dir, '*.plist'))))

    def test_analyze_only_file_option(self):
        """
        Test analyze command --file option without a skip file.
        """
        self.__log_and_analyze_simple([
            "--file", "*/skip_header.cpp"])
        self.assertFalse(
            any('skip_header.cpp' not in f for f in glob.glob(
                os.path.join(self.report_dir, '*.plist'))))

    def test_parse_file_option(self):
        """ Test parse command --file option. """
        skipfile = os.path.join(self.test_dir, "simple", "skipfile")

        self.__log_and_analyze_simple()

        # Only reports from the given files are returned.
        out, _, returncode = self.__run_parse(
            ["--file", "*/skip_header.cpp"])
        self.assertEqual(returncode, 2)
        data = json.loads(out)
        self.assertTrue(len(data['reports']))
        self.assertTrue(all(
            r['file']['original_path'].endswith('/skip_header.cpp')
            for r in data['reports']))

        # The given file is skipped by the skipfile.
        _, _, returncode = self.__run_parse(
            ["--file", "*/file_to_be_skipped.cpp", "--ignore", skipfile])
        self.assertEqual(returncode, 0)

        # The given file is not skipped by the skip file.
        out, _, returncode = self.__run_parse(
            ["--file", "*/skip_header.cpp", "--ignore", skipfile])
        self.assertEqual(returncode, 2)
        data = json.loads(out)
        self.assertTrue(len(data['reports']))
        self.assertTrue(all(
            r['file']['original_path'].endswith('/skip_header.cpp')
            for r in data['reports']))
