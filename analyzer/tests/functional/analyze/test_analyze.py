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
import unittest
import zipfile

from libtest import env

from codechecker_analyzer.analyzers.clangsa import version


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

        self.missing_checker_regex = re.compile(
            r"No checker\(s\) with these names was found")

    def tearDown(self):
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

    @unittest.skipIf(version.get("gcc") is not None,
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
            source.write('''{
  "clang++": {
    "c++": {
      "compiler_standard": "-std=FAKE_STD",
      "target": "FAKE_TARGET",
      "compiler_includes": [
        "-isystem /FAKE_INCLUDE_DIR"
      ]
    }
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

    def unique_json_helper(self, unique_json, is_a, is_b, is_s):
        with open(unique_json,
                  encoding="utf-8", errors="ignore") as json_file:
            data = json.load(json_file)
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

        self.unique_json_helper(unique_json, True, False, True)

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

        self.unique_json_helper(unique_json, False, True, True)

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
        self.unique_json_helper(unique_json, True, True, True)

    def test_invalid_enabled_checker_name(self):
        """Warn in case of an invalid enabled checker."""
        build_json = os.path.join(self.test_workspace, "build_success.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "-e", "non-existing-checker-name"]

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

        match = self.missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        errcode = process.returncode
        self.assertEqual(errcode, 0)

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

    def test_invalid_disabled_checker_name(self):
        """Warn in case of an invalid disabled checker."""
        build_json = os.path.join(self.test_workspace, "build_success.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir,
                       "-d", "non-existing-checker-name"]

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

        match = self.missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)

        errcode = process.returncode
        self.assertEqual(errcode, 0)

    def test_multiple_invalid_checker_names(self):
        """Warn in case of multiple invalid checker names."""
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

        match = self.missing_checker_regex.search(out)
        self.assertIsNotNone(match)
        self.assertTrue("non-existing-checker-name" in out)
        self.assertTrue("non-existing-checker" in out)
        self.assertTrue("missing.checker" in out)
        self.assertTrue("other.missing.checker" in out)

        errcode = process.returncode

        self.assertEqual(errcode, 0)

    def test_makefile_generation(self):
        """ Test makefile generation. """
        build_json = os.path.join(self.test_workspace, "build_extra_args.json")
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "-o", self.report_dir, '--makefile']

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

        print(out)
        # First it's printed as the member of enabled checkers at the beginning
        # of the output. Second it is printed as a found report.
        self.assertEqual(out.count('hicpp-use-nullptr'), 1)

        analyze_cmd = [self._codechecker_cmd, "check", "-l", build_json,
                       "--analyzers", "clang-tidy", "-o", self.report_dir,
                       "--analyzer-config",
                       "clang-tidy:Checks=hicpp-use-nullptr",
                       "--checker-config",
                       "clang-tidy:hicpp-use-nullptr.NullMacros=MY_NULL"]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.test_dir,
            encoding="utf-8",
            errors="ignore")
        out, _ = process.communicate()

        # First it's printed as the member of enabled checkers at the beginning
        # of the output. Second and third it is printed as a found report.
        self.assertEqual(out.count('hicpp-use-nullptr'), 2)

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
        # First it's printed as the member of enabled checkers at the beginning
        # of the output. Second it is printed as a found report.
        self.assertEqual(out.count('UninitializedObject'), 2)

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
