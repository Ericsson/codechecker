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
import shutil

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
        if os.path.isdir(self.report_dir):
            shutil.rmtree(self.report_dir)

    def __get_plist_files(self, reportdir):
        return [os.path.join(reportdir, filename)
                for filename in os.listdir(reportdir)
                if filename.endswith('.plist')]

    def __analyze_incremental(self, content_, build_json, reports_dir,
                              plist_count, failed_count):
        """
        Helper function to test analyze incremental mode. It's create a file
        with the given content. Run analyze on that file and checks the count
        of the plist end error files.
        """
        source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Write content to the test file
        with open(source_file, 'w') as source:
            source.write(content_)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        # Run analyze
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        process.communicate()

        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # Check the count of the plist files.
        plist_files = [os.path.join(reports_dir, filename)
                       for filename in os.listdir(reports_dir)
                       if filename.endswith('.plist')]
        self.assertEquals(len(plist_files), plist_count)

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
        self.assertEquals(failed_file_count, failed_count)

    def test_compiler_info_files(self):
        '''
        Test that the compiler info files are generated
        '''
        # GIVEN
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        reports_dir = self.report_dir
        source_file = os.path.join(self.test_workspace, "simple.cpp")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      },
                     {"directory": self.test_workspace,
                      "command": "clang -c " + source_file,
                      "file": source_file
                      }
                     ]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        # Test file contents
        simple_file_content = "int main() { return 0; }"

        # Write content to the test file
        with open(source_file, 'w') as source:
            source.write(simple_file_content)

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", reports_dir]

        # WHEN
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        process.communicate()

        # THEN
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        from libcodechecker.analyze.log_parser import\
            compiler_includes_dump_file
        from libcodechecker.analyze.log_parser import compiler_target_dump_file
        includes_File = os.path.join(reports_dir, compiler_includes_dump_file)
        target_File = os.path.join(reports_dir, compiler_target_dump_file)
        self.assertEquals(os.path.exists(includes_File), True)
        self.assertEquals(os.path.exists(target_File), True)
        self.assertNotEqual(os.stat(includes_File).st_size, 0)
        self.assertNotEqual(os.stat(target_File).st_size, 0)

        # Test the validity of the json files.
        with open(includes_File, 'r') as f:
            try:
                data = json.load(f)
                self.assertEquals(len(data), 2)
                self.assertTrue("clang" in data)
                self.assertTrue("gcc" in data)
            except ValueError:
                self.fail("json.load should successfully parse the file %s"
                          % includes_File)
        with open(target_File, 'r') as f:
            try:
                data = json.load(f)
                self.assertEquals(len(data), 2)
                self.assertTrue("clang" in data)
                self.assertTrue("gcc" in data)
            except ValueError:
                self.fail("json.load should successfully parse the file %s"
                          % target_File)

    def test_compiler_includes_file_is_loaded(self):
        '''
        Test that the compiler includes file is read when the specific command
        line switch is there.
        '''
        reports_dir = self.report_dir
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        source_file = os.path.join(self.test_workspace, "simple.cpp")
        compiler_includes_file = os.path.join(self.test_workspace,
                                              "compiler_includes_file.json")

        # Contents of build log.
        build_log = [
                     {"directory": self.test_workspace,
                      "command": "clang -c " + source_file,
                      "file": source_file
                      }
                     ]
        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        # Test file contents.
        simple_file_content = "int main() { return 0; }"
        # Write content to the test file.
        with open(source_file, 'w') as source:
            source.write(simple_file_content)

        with open(compiler_includes_file, 'w') as source:
            source.write(
                # Raw string literal, cannot break the line:
                r"""{"clang": "\"\n#include \"...\" search starts here:\n"""\
                r"""#include <...> search starts here:\n"""\
                r""" /TEST_FAKE_INCLUDE_DIR"}"""
            )

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--compiler-includes-file", compiler_includes_file,
                       "--verbose", "debug",
                       "-o", reports_dir]
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        out, _ = process.communicate()

        self.assertTrue("-isystem /TEST_FAKE_INCLUDE_DIR" in out)

    def test_compiler_target_file_is_loaded(self):
        '''
        Test that the compiler target file is read when the specific command
        line switch is there
        '''
        reports_dir = self.report_dir
        build_json = os.path.join(self.test_workspace, "build_simple.json")
        source_file = os.path.join(self.test_workspace, "simple.cpp")
        compiler_target_file = os.path.join(self.test_workspace,
                                            "compiler_target_file.json")

        # Contents of build log.
        build_log = [
                     {"directory": self.test_workspace,
                      "command": "clang -c " + source_file,
                      "file": source_file
                      }
                     ]
        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        # Test file contents.
        simple_file_content = "int main() { return 0; }"
        # Write content to the test file.
        with open(source_file, 'w') as source:
            source.write(simple_file_content)

        with open(compiler_target_file, 'w') as source:
            source.write(
                # Raw string literal, cannot break the line:
                r"""{"clang": "Target: TEST_FAKE_TARGET\nConfigured with"}"""
            )

        # Create analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--compiler-target-file", compiler_target_file,
                       "--verbose", "debug",
                       "-o", reports_dir]
        # Run analyze.
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        out, _ = process.communicate()

        self.assertTrue("--target=TEST_FAKE_TARGET" in out)

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
        print(out + err)
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
        source_file = os.path.join(self.test_dir, "failure.c")

        # Create a compilation database.
        build_log = [{"directory": self.test_workspace,
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
            json.dump(build_log, outfile)

        # Create and run analyze command.
        analyze_cmd = [self._codechecker_cmd, "analyze", build_json,
                       "--analyzers", "clangsa", "-o", self.report_dir]

        print(analyze_cmd)
        process = subprocess.Popen(
            analyze_cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=self.test_dir)
        process.communicate()

        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect a failure archive to be in the failed directory.
        failed_files = os.listdir(failed_dir)
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
        print(out + err)
        errcode = process.returncode
        self.assertEquals(errcode, 0)

        # We expect a failure archive to be in the failed directory.
        failed_files = os.listdir(failed_dir)
        print(failed_files)
        self.assertEquals(len(failed_files), 1)
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
                      "command": "gcc -c " + source_file,
                      "file": source_file
                      }]

        with open(build_json, 'w') as outfile:
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
