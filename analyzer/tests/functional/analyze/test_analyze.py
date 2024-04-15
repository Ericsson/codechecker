#
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test case for the CodeChecker analyze command's direct functionality.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import shlex
import unittest
import zipfile

from libtest import env

from codechecker_report_converter.report import report_file
from codechecker_analyzer.analyzers.clangsa import version


class TestAnalyze(unittest.TestCase):
    _ccClient = None

    def setup_class(self):
        """Setup the environment for the tests."""

        global TEST_WORKSPACE
        TEST_WORKSPACE = env.get_workspace('analyze')

        report_dir = os.path.join(TEST_WORKSPACE, 'reports')
        os.makedirs(report_dir)

        os.environ['TEST_WORKSPACE'] = TEST_WORKSPACE

    def teardown_class(self):
        """Delete the workspace associated with this test"""

        print("Removing: " + TEST_WORKSPACE)
        shutil.rmtree(TEST_WORKSPACE)

    def setup_method(self, method):
        """Setup the environment for the tests."""

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

        self.warn_missing_checker_regex = re.compile(
            r"WARNING.*No checker\(s\) with these names was found")

        self.err_missing_checker_regex = re.compile(
            r"ERROR.*No checker\(s\) with these names was found")

        self.disabling_modeling_checker_regex = re.compile(
            r"analyzer-disable-checker=.*unix.cstring.CStringModeling.*")

    def teardown_method(self, method):
        """Restore environment after tests have ran."""
        os.chdir(self.__old_pwd)
        if os.path.isdir(self.report_dir):
            shutil.rmtree(self.report_dir)

    def __analyze_incremental(self, content_, build_json, reports_dir,
                              plist_count, failed_count):
        """
        Helper function to test analyze incremental mode. It's create a file
        with the given content. Run analyze on that file and checks the count
        of the plist end error files.
        """
        source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Write content to the test file
        with open(source_file, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(content_)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        # Run analyze
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        print(out)
        print(err)

        errcode = process.returncode
        # This function checks incremental analysis. There are some test cases
        # for failed analysis during incremental analysis, do the error code
        # can also be 3.
        self.assertIn(errcode, [0, 3])

        # Check the count of the plist files.
        plist_files = [os.path.join(reports_dir, filename)
                       for filename in os.listdir(reports_dir)
                       if filename.endswith('.plist')]
        self.assertEqual(len(plist_files), plist_count)

        # Check the count of the error files.
        failed_dir = os.path.join(reports_dir, "failed")
        failed_file_count = 0
        if os.path.exists(failed_dir):
            failed_files = [os.path.join(failed_dir, filename)
                            for filename in os.listdir(failed_dir)
                            if filename.endswith('.zip')]
            failed_file_count = len(failed_files)

            for f in failed_files:
                os.remove(f)
        self.assertEqual(failed_file_count, failed_count)

    @unittest.skipUnless(
        version.get("gcc"),
        "If gcc or g++ is a symlink to clang this test should be "
        "skipped. Option filtering is different for the two "
        "compilers. This test is gcc/g++ specific.")
    def test_compiler_info_files(self):
        '''
        Test that the compiler info files are generated
        '''
        # GIVEN
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        reports_dir = self.report_dir
        source_file_cpp = os.path.join(self.test_workspace, "simple.cpp")
        source_file_c = os.path.join(self.test_workspace, "simple.c")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file_c,
                      "file": source_file_c
                      },
                     {"directory": self.test_workspace,
                      "command": "clang++ -c " + source_file_cpp,
                      "file": source_file_cpp
                      }
                     ]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = "int main() { return 0; }"

        # Write content to the test file
        with open(source_file_cpp, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

        with open(source_file_c, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        # WHEN
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # THEN
        errcode = process.returncode
        self.assertEqual(errcode, 0)

        info_File = os.path.join(reports_dir, 'compiler_info.json')
        self.assertEqual(os.path.exists(info_File), True)
        self.assertNotEqual(os.stat(info_File).st_size, 0)

        # Test the validity of the json files.
        with open(info_File, 'r', encoding="utf-8", errors="ignore") as f:
            try:
                data = json.load(f)
                self.assertEqual(len(data), 1)
                # For clang we do not collect anything.
                self.assertTrue("g++" in data)
            except ValueError:
                self.fail("json.load should successfully parse the file %s"
                          % info_File)

    def test_compiler_info_file_is_loaded(self):
        '''
        Test that compiler info file is loaded if option is set.
        '''
        reports_dir = self.report_dir
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        source_file = os.path.join(self.test_workspace, "simple.cpp")
        compiler_info_file = os.path.join(self.test_workspace,
                                          "compiler_info.json")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "clang++ -c " + source_file,
                      "file": source_file}]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = "int main() { return 0; }"

        # Write content to the test file
        with open(source_file, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(simple_file_content)

        with open(compiler_info_file, 'w',
                  encoding="utf-8", errors="ignore") as source:
            source.write(r'''{
  "[\"clang++\", \"c++\", []]": {
    "compiler_includes": ["/FAKE_INCLUDE_DIR"],
    "compiler_standard": "-std=FAKE_STD",
    "target": "FAKE_TARGET"
  }
}''')

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--compiler-info-file", compiler_info_file,
                       "--analyzers", "clangsa", "--verbose", "debug",
                       "-o", reports_dir]
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()
        print(out)
        self.assertTrue("-std=FAKE_STD" in out)
        self.assertTrue("--target=FAKE_TARGET" in out)
        self.assertTrue("-isystem /FAKE_INCLUDE_DIR" in out)

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

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        print(out)
        print(err)
        errcode = process.returncode
        self.assertEqual(errcode, 0)

        # We expect the sucess stderr file in the success directory.
        success_files = os.listdir(success_dir)
        print(success_files)
        self.assertEqual(len(success_files), 1)
        self.assertIn("success.c", success_files[0])
        os.remove(os.path.join(success_dir, success_files[0]))

    def test_failure(self):
        """
        Test if reports/failed/<failed_file>.zip file is created
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        failed_dir = os.path.join(self.report_dir, "failed")
        source_file = os.path.join(self.test_dir, "failure.c")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Create and run analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "--verbose", "debug",
                       "-o", self.report_dir]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)
        errcode = process.returncode
        self.assertEqual(errcode, 3)

        self.assertNotIn("UserWarning: Duplicate name", err)

        # We expect a failure archive to be in the failed directory.
        failed_files = os.listdir(failed_dir)
        self.assertEqual(len(failed_files), 1)

        fail_zip = os.path.join(failed_dir, failed_files[0])

        with zipfile.ZipFile(fail_zip, 'r') as archive:
            files = archive.namelist()

            self.assertIn("build-action", files)
            self.assertIn("analyzer-command", files)

            with archive.open("build-action", 'r') as archived_buildcmd:
                self.assertEqual(archived_buildcmd.read().decode("utf-8"),
                                 "gcc -c " + source_file)

            source_in_archive = os.path.join("sources-root",
                                             source_file.lstrip('/'))
            self.assertIn(source_in_archive, files)

            with archive.open(source_in_archive, 'r') as archived_code:
                with open(source_file, 'r',
                          encoding="utf-8", errors="ignore") as source_code:
                    self.assertEqual(archived_code.read().decode("utf-8"),
                                     source_code.read())

        shutil.rmtree(failed_dir)

    def test_reproducer(self):
        """
        Test if reports/reproducer/<reproducer_file>.zip file is created
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        reproducer_dir = os.path.join(self.report_dir, "reproducer")
        source_file = os.path.join(self.test_dir, "failure.c")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Create and run analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "--verbose", "debug",
                       "-o", self.report_dir, "--generate-reproducer", "-c"]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()

        print(out)
        print(err)
        errcode = process.returncode
        self.assertEqual(errcode, 3)
        self.assertNotIn('failed', os.listdir(self.report_dir))

        self.assertNotIn("UserWarning: Duplicate name", err)

        # We expect a failure archive to be in the failed directory.
        reproducer_files = os.listdir(reproducer_dir)
        self.assertEqual(len(reproducer_files), 1)

        fail_zip = os.path.join(reproducer_dir, reproducer_files[0])

        with zipfile.ZipFile(fail_zip, 'r') as archive:
            files = archive.namelist()

            self.assertIn("build-action", files)
            self.assertIn("analyzer-command", files)

            with archive.open("build-action", 'r') as archived_buildcmd:
                self.assertEqual(archived_buildcmd.read().decode("utf-8"),
                                 "gcc -c " + source_file)

            source_in_archive = os.path.join("sources-root",
                                             source_file.lstrip('/'))
            self.assertIn(source_in_archive, files)

            with archive.open(source_in_archive, 'r') as archived_code:
                with open(source_file, 'r',
                          encoding="utf-8", errors="ignore") as source_code:
                    self.assertEqual(archived_code.read().decode("utf-8"),
                                     source_code.read())

        shutil.rmtree(reproducer_dir)

    def test_robustness_for_dependencygen_failure(self):
        """
        Test if failure ZIP is created even if the dependency generator creates
        an invalid output.
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        failed_dir = os.path.join(self.report_dir, "failed")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "--verbose", "debug",
                       "-o", self.report_dir]

        source_file = os.path.join(self.test_dir, "failure.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "cc -c -std=c++11 " + source_file,
                      "file": source_file
                      }]

        # cc -std=c++11 writes error "-std=c++11 valid for C++ but not for C"
        # to its output when invoked as a dependency generator for this
        # build command.

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 3)

        # We expect a failure archive to be in the failed directory.
        failed_files = os.listdir(failed_dir)
        print(failed_files)
        self.assertEqual(len(failed_files), 1)
        self.assertIn("failure.c", failed_files[0])

        os.remove(os.path.join(failed_dir, failed_files[0]))

    def test_incremental_analyze(self):
        """
        Test incremental mode to analysis command which overwrites only those
        plist files that were update by the current build command.
        """
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        reports_dir = os.path.join(self.test_workspace, "reports_incremental")
        source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "g++ -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = "int main() { return 0; }"
        failed_file_content = "int main() { err; return 0; }"

        # Run analyze on the simple file.
        self.__analyze_incremental(simple_file_content, build_json,
                                   reports_dir, 1, 0)

        # Run analyze on the failed file.
        self.__analyze_incremental(failed_file_content, build_json,
                                   reports_dir, 0, 1)

        # Run analyze on the simple file again.
        self.__analyze_incremental(simple_file_content, build_json,
                                   reports_dir, 1, 0)

    def test_relative_include_paths(self):
        """
        Test if the build json contains relative paths.
        """
        build_json = os.path.join(self.test_workspace, "build_simple_rel.json")
        report_dir = os.path.join(self.test_workspace, "reports_relative")
        source_file = os.path.join(self.test_dir, "simple.c")
        failed_dir = os.path.join(report_dir, "failed")

        # Create a compilation database.
        build_log = [{"directory": self.test_dir,
                      "command": "cc -c " + source_file + " -Iincludes",
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", report_dir]
        # CodeChecker is executed in a different
        # dir than the containing folder of simple.c.
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)
        self.assertFalse(os.path.isdir(failed_dir))

    def test_tidyargs_saargs(self):
        """
        Test tidyargs and saargs config files
        """
        build_json = os.path.join(self.test_workspace, "build_extra_args.json")
        report_dir = os.path.join(self.test_workspace, "reports_extra_args")
        source_file = os.path.join(self.test_dir, "extra_args.cpp")
        tidyargs_file = os.path.join(self.test_dir, "tidyargs")
        saargs_file = os.path.join(self.test_dir, "saargs")

        build_log = [{"directory": self.test_dir,
                      "command": "g++ -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "-o", report_dir, "--tidyargs", tidyargs_file,
                       "--analyzer-config", 'clang-tidy:HeaderFilterRegex=.*',
                       'clang-tidy:Checks=modernize-use-bool-literals']

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        process = subprocess.Popen(
            [self._codechecker_cmd, "parse", report_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        self.assertIn("division by zero", out)
        self.assertIn("modernize-avoid-bind", out)
        self.assertNotIn("performance-for-range-copy", out)

        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "-o", report_dir, "--saargs", saargs_file]
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        process = subprocess.Popen(
            [self._codechecker_cmd, "parse", report_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        self.assertIn("Dereference of null pointer", out)

    def check_unique_compilation_db(
        self,
        compilation_db_file_path: str,
        num_of_compile_commands: int,
        is_a: bool,
        is_b: bool,
        is_s: bool
    ):
        """ """
        with open(compilation_db_file_path,
                  encoding="utf-8", errors="ignore") as json_file:
            data = json.load(json_file)
            self.assertEqual(len(data), num_of_compile_commands)

            simple_a = False
            simple_b = False
            success = False
            for d in data:
                if "simple_a.o" in d["command"]:
                    simple_a = True
                if "simple_b.o" in d["command"]:
                    simple_b = True
                if "success.o" in d["command"]:
                    success = True
            self.assertEqual(simple_a, is_a)
            self.assertEqual(simple_b, is_b)
            self.assertEqual(success, is_s)

    def test_compile_uniqueing(self):
        """
        Test complilation uniqueing
        """
        build_json = os.path.join(self.test_workspace, "build_simple_rel.json")
        report_dir = os.path.join(self.test_workspace, "reports_relative")
        source_file = os.path.join(self.test_dir, "simple.c")
        source_file2 = os.path.join(self.test_dir, "success.c")
        failed_dir = os.path.join(report_dir, "failed")
        unique_json = os.path.join(report_dir, "unique_compile_commands.json")

        # Create a compilation database.
        build_log = [{"directory": self.test_dir,
                      "command": "cc -c " + source_file +
                      " -Iincludes -o simple_b.o",
                      "file": source_file},
                     {"directory": self.test_dir,
                      "command": "cc -c " + source_file +
                      " -Iincludes -o simple_a.o",
                      "file": source_file},
                     {"directory": self.test_dir,
                      "command": "cc -c " + source_file +
                      " -Iincludes -o simple_a.o",
                      "file": source_file},
                     {"directory": self.test_dir,
                      "command": "cc -c " + source_file2 +
                      " -Iincludes -o success.o",
                      "file": source_file2}]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Testing alphabetic uniqueing mode.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", report_dir,
                       "--compile-uniqueing", "alpha"]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)
        self.assertFalse(os.path.isdir(failed_dir))

        self.check_unique_compilation_db(unique_json, 2, True, False, True)

        # Testing regex mode.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", report_dir,
                       "--compile-uniqueing", ".*_b.*"]
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)
        self.assertFalse(os.path.isdir(failed_dir))

        self.check_unique_compilation_db(unique_json, 2, False, True, True)

        # Testing regex mode.error handling
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", report_dir,
                       "--compile-uniqueing", ".*simple.*"]
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        # Since .*simple.* matches 2 files, thus we get an error
        self.assertEqual(errcode, 1)

        # Testing strict mode
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", report_dir,
                       "--compile-uniqueing", "strict", "--verbose", "debug"]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        # In strict mode the analysis must fail
        # if there are more than one build
        # commands for a single source.
        errcode = process.returncode
        self.assertEqual(errcode, 1)
        self.assertFalse(os.path.isdir(failed_dir))

        # Testing None mode.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", report_dir,
                       "--compile-uniqueing", "none"]
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_workspace,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)
        self.assertFalse(os.path.isdir(failed_dir))
        self.check_unique_compilation_db(unique_json, 3, True, True, True)

    def __run_with_invalid_checker_name(self, codechecker_subcommand,
                                        extra_args):
        analyze_cmd = codechecker_subcommand + extra_args

        print(shlex.join(analyze_cmd))
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, err = process.communicate()
        return out, err, process.returncode

    def __run_with_invalid_enabled_checker_name_common(self,
                                                       codechecker_subcommand,
                                                       extra_args):
        return self.__run_with_invalid_checker_name(
            codechecker_subcommand + ["--analyzers", "clangsa", "-o",
                                      self.report_dir, "-c", "-e",
                                      "non-existing-checker-name"], extra_args)

    def __get_build_json(self):
        build_json = os.path.join(self.test_workspace, "build_success.json")
        source_file = os.path.join(self.test_dir, "success.c")
        build_log = [{
            "directory": self.test_workspace,
            "command": "gcc -c " + source_file,
            "file": source_file}]
        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)
        return build_json

    def __run_with_invalid_enabled_checker_name_check(self, extra_args):
        codechecker_subcommand = [self._codechecker_cmd, "check", "-l",
                                  self.__get_build_json()]
        return self.__run_with_invalid_enabled_checker_name_common(
                codechecker_subcommand, extra_args)

    def __run_with_invalid_enabled_checker_name_analyze(self, extra_args):
        build_json = os.path.join(self.test_workspace, "build_success.json")
        codechecker_subcommand = [self._codechecker_cmd, "analyze",
                                  self.__get_build_json()]
        return self.__run_with_invalid_enabled_checker_name_common(
                codechecker_subcommand, extra_args)

    def test_invalid_enabled_checker_name(self):
        """Error out in case of an invalid enabled checker."""
        out, err, errcode = \
            self.__run_with_invalid_enabled_checker_name_check([])

        match = self.err_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        self.assertEqual(errcode, 1)

        out, _, errcode = \
            self.__run_with_invalid_enabled_checker_name_analyze([])

        match = self.err_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        self.assertEqual(errcode, 1)

    def test_invalid_enabled_checker_name_warn(self):
        """
        Warn in case of an invalid enabled checker when using
        --no-missing-checker-error.
        """
        out, _, errcode = self.__run_with_invalid_enabled_checker_name_analyze(
            ['--no-missing-checker-error'])

        match = self.warn_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        self.assertEqual(errcode, 0)

        out, _, errcode = self.__run_with_invalid_enabled_checker_name_check(
            ['--no-missing-checker-error'])

        print(out)
        match = self.warn_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        # FIXME: Interestingly, CodeChecker analyze doesn't find the bug in the
        # code, but CodeChecker check does, so the return value is 2 here
        # instead of 0. Lets just check that its not a CodeChecker error (which
        # would be a return code of 1).
        self.assertNotEqual(errcode, 1)

    def test_disable_all_warnings(self):
        """Test disabling warnings as checker groups."""
        build_json = os.path.join(self.test_workspace, "build.json")
        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--analyzers", "clang-tidy",
                       "-d", "clang-diagnostic",
                       "-e", "clang-diagnostic-unused"]

        source_file = os.path.join(self.test_dir, "compiler_warning.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        self.assertNotIn("format specifies type 'int' but the argument has "
                         "type 'char *' [clang-diagnostic-format]", out)
        self.assertIn("unused variable 'i' [clang-diagnostic-unused-variable]",
                      out)

    def __run_with_invalid_disabled_checker_name_common(self,
                                                        codechecker_subcommand,
                                                        extra_args):
        return self.__run_with_invalid_checker_name(
            codechecker_subcommand + ["--analyzers", "clangsa", "-o",
                                      self.report_dir, "-c", "-d",
                                      "non-existing-checker-name"], extra_args)

    def __run_with_invalid_disabled_checker_name_check(self, extra_args):
        codechecker_subcommand = [self._codechecker_cmd, "check", "-l",
                                  self.__get_build_json()]
        return self.__run_with_invalid_disabled_checker_name_common(
                codechecker_subcommand, extra_args)

    def __run_with_invalid_disabled_checker_name_analyze(self, extra_args):
        build_json = os.path.join(self.test_workspace, "build_success.json")
        codechecker_subcommand = [self._codechecker_cmd, "analyze",
                                  self.__get_build_json()]
        return self.__run_with_invalid_disabled_checker_name_common(
                codechecker_subcommand, extra_args)

    def test_invalid_disabled_checker_name(self):
        """Error out in case of an invalid disabled checker."""
        out, _, errcode = \
            self.__run_with_invalid_disabled_checker_name_analyze([])

        match = self.err_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        self.assertEqual(errcode, 1)

        out, _, errcode = \
            self.__run_with_invalid_disabled_checker_name_check([])

        match = self.err_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        self.assertEqual(errcode, 1)

    def test_invalid_disabled_checker_name_warn(self):
        """
        Warn in case of an invalid disabled checker when using
        --no-missing-checker-error.
        """
        out, _, errcode = \
            self.__run_with_invalid_disabled_checker_name_analyze(
                ['--no-missing-checker-error'])

        match = self.warn_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        self.assertEqual(errcode, 0)

        out, _, errcode = self.__run_with_invalid_disabled_checker_name_check(
            ['--no-missing-checker-error'])

        match = self.warn_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        # FIXME: Interestingly, CodeChecker analyze doesn't find the bug in the
        # code, but CodeChecker check does, so the return value is 2 here
        # instead of 0. Lets just check that its not a CodeChecker error (which
        # would be a return code of 1).
        self.assertNotEqual(errcode, 1)

    def test_disabling_clangsa_modeling_checkers(self):
        """Warn in case a modeling checker is disabled from clangsa"""
        build_json = os.path.join(self.test_workspace, "build_success.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "-d", "unix", "--verbose", "debug_analyzer"]

        source_file = os.path.join(self.test_dir, "success.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        match = self.disabling_modeling_checker_regex.search(out)
        self.assertIsNone(match)

        errcode = process.returncode
        self.assertEqual(errcode, 0)

    def test_multiple_invalid_checker_names(self):
        """Error out in case of multiple invalid checker names."""
        build_json = os.path.join(self.test_workspace, "build_success.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "-e", "non-existing-checker-name",
                       "-e", "non-existing-checker",
                       "-d", "missing.checker",
                       "-d", "other.missing.checker"]

        source_file = os.path.join(self.test_dir, "success.c")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        match = self.warn_missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)
        self.assertTrue("non-existing-checker" in out)
        self.assertTrue("missing.checker" in out)
        self.assertTrue("other.missing.checker" in out)

        errcode = process.returncode

        self.assertEqual(errcode, 1)

    def test_cppcheck_standard(self):
        """
        Testing the standard ("--std") compiler paramater translation
        to cppcheck input parameter.
        Cppcheck can only understand a subset of the available options.
        """
        build_json = os.path.join(self.test_workspace, "cppcheck_std.json")
        analyze_cmd = [self._codechecker_cmd, "analyze",
                       build_json,
                       "--analyzers", "cppcheck",
                       "-o", self.report_dir, "--verbose",
                       "debug_analyzer"]
        source_file = os.path.join(self.test_dir, "simple.c")

        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c -std=c99 " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        out = subprocess.run(analyze_cmd,
                             cwd=self.test_dir,
                             # env=self.env,
                             stdout=subprocess.PIPE).stdout.decode()

        # Test correct handover.
        self.assertTrue("--std=c99" in out)

        # Cppcheck does not support gnu variants of the standards,
        # These are transformed into their respective c and c++
        # varinats inside CodeChecker
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c -std=gnu99 " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        out = subprocess.run(analyze_cmd,
                             cwd=self.test_dir,
                             # env=self.env,
                             stdout=subprocess.PIPE).stdout.decode()

        # Test if the standard is correctly transformed
        self.assertTrue("--std=c99" in out)

    def test_makefile_generation(self):
        """ Test makefile generation. """
        build_json = os.path.join(self.test_workspace, "build_extra_args.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "-o", self.report_dir,
                       "-e", "clang-diagnostic",
                       '--makefile']

        source_file = os.path.join(self.test_dir, "extra_args.cpp")
        build_log = [{"directory": self.test_workspace,
                      "command": "g++ -DTIDYARGS -c " + source_file,
                      "file": source_file
                      },
                     {"directory": self.test_workspace,
                      "command": "g++ -DSAARGS -DTIDYARGS -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)

        # Check the existence of the Makefile.
        makefile = os.path.join(self.report_dir, 'Makefile')
        self.assertTrue(os.path.exists(makefile))

        # Run the generated Makefile and check the return code of it.
        process = subprocess.Popen(["make"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   cwd=self.report_dir,
                                   encoding="utf-8",
                                   errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)

        plist_files = glob.glob(os.path.join(self.report_dir, '*.plist'))
        self.assertEqual(len(plist_files), 4)

    def test_disable_all_checkers(self):
        """
        If all checkers of an analyzer are disabled then the analysis shouldn't
        trigger for that analyzer.
        """
        build_json = os.path.join(self.test_workspace, "build.json")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c main.c",
                      "file": "main.c"}]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        for analyzer in ['clangsa', 'clang-tidy']:
            analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                           "--analyzers", analyzer,
                           "--disable", "default"]
            process = subprocess.Popen(
                analyze_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="ignore")
            out, _ = process.communicate()

            self.assertIn(f"No checkers enabled for {analyzer}", out)

        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--disable-all"]
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        # Checkers of all 3 analyzers are disabled.
        self.assertEqual(out.count("No checkers enabled for"), 4)

    def test_analyzer_and_checker_config(self):
        """Test analyzer configuration through command line flags."""
        build_json = os.path.join(self.test_workspace, "build_success.json")
        source_file = os.path.join(self.test_dir, "checker_config.cpp")
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file}]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--analyzers", "clang-tidy", "-o", self.report_dir,
                       "--analyzer-config",
                       "clang-tidy:Checks=hicpp-use-nullptr"]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        # It's printed as a found report and in the checker statistics.
        # Note: If this test case fails, its pretty sure that something totally
        # unrelated to the analysis broke in CodeChecker. Print both the
        # stdout and stderr streams from the above communicate() call (the
        # latter of which is ignored with _ above).
        self.assertEqual(out.count('hicpp-use-nullptr'), 2)

        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--analyzers", "clang-tidy", "-o", self.report_dir,
                       "--analyzer-config",
                       "clang-tidy:Checks=hicpp-use-nullptr",
                       "--checker-config",
                       "clang-tidy:hicpp-use-nullptr:NullMacros=MY_NULL"]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        # It's printed as the member of enabled checkers at the beginning
        # of the output, a found report and in the checker statistics.
        self.assertEqual(out.count('hicpp-use-nullptr'), 3)

        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "--checker-config",
                       "clangsa:optin.cplusplus.UninitializedObject:Pedantic"
                       "=true"]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()
        print(out)
        # It's printed as the member of enabled checkers at the beginning
        # of the output, a found report and in the checker statistics.
        self.assertEqual(out.count('UninitializedObject'), 3)

        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "--checker-config",
                       "clangsa:optin.cplusplus.UninitializedObject:Pedantic"
                       "=true",
                       "--analyzer-config",
                       "clangsa:max-nodes=1"]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        print(out)
        # It is printed as the member of enabled checkers, but it gives no
        # report.
        self.assertEqual(out.count('UninitializedObject'), 1)

    def test_invalid_compilation_database(self):
        """ Warn in case of an invalid enabled checker. """
        build_json = os.path.join(self.test_workspace, "build_corrupted.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "-o", self.report_dir]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            outfile.write("Corrupted JSON file!")

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")

        process.communicate()

        self.assertEqual(process.returncode, 1)

    def test_compilation_db_relative_file_path(self):
        """
        Test relative path in compilation database.

        If the file/directory paths in the compilation database are relative
        ClangSA analyzer will generate plist files where the file paths are
        also relative to the current directory where the analyzer was executed.
        After the plist files are created, report converter will try to
        post-process these files and creates absolute paths from the relative
        paths. This test will check whether these files paths are exist.
        """
        test_dir = os.path.join(self.test_workspace, "test_rel_file_path")
        os.makedirs(test_dir)

        source_file_name = "success.c"
        shutil.copy(os.path.join(self.test_dir, source_file_name), test_dir)

        cc_files_dir_path = os.path.join(test_dir, "codechecker_files")
        os.makedirs(cc_files_dir_path, exist_ok=True)

        build_json = os.path.join(cc_files_dir_path, "build.json")
        report_dir = os.path.join(cc_files_dir_path, "reports")

        # Create a compilation database.
        build_log = [{
            "directory": ".",
            "command": f"cc -c {source_file_name} -o /dev/null",
            "file": source_file_name}]

        with open(build_json, 'w',
                  encoding="utf-8", errors="ignore") as outfile:
            json.dump(build_log, outfile)

        # Analyze the project
        analyze_cmd = [
            self._codechecker_cmd, "analyze",
            build_json,
            "--report-hash", "context-free-v2",
            "-o", report_dir,
            "--clean"]

        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=test_dir,
            encoding="utf-8",
            errors="ignore")
        process.communicate()

        errcode = process.returncode
        self.assertEqual(errcode, 0)

        # Test that file paths in plist files are exist.
        plist_files = glob.glob(os.path.join(report_dir, '*.plist'))
        for plist_file in plist_files:
            reports = report_file.get_reports(plist_file)
            for r in reports:
                for file in r.files:
                    self.assertTrue(os.path.exists(file.original_path))
