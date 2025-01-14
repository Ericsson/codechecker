# Copyright 2023 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit and functional tests
"""
import logging
import os
import re
import shlex
import subprocess
import sys
import unittest


class TestBase(unittest.TestCase):
    """Unittest base abstract class"""

    BAZEL_BIN_DIR = os.path.join("..", "bazel-bin", "test")
    BAZEL_TESTLOGS_DIR = os.path.join("..", "bazel-testlogs", "test")

    @classmethod
    def setUpClass(cls):
        """Load module, save environment"""
        # Save environment and location
        cls.save_env = os.environ
        cls.save_cwd = os.getcwd()
        # Move to test dir
        cls.test_dir = os.path.abspath(os.path.dirname(__file__))
        os.chdir(cls.test_dir)

    @classmethod
    def tearDownClass(cls):
        """Restore environment"""
        os.chdir(cls.save_cwd)
        os.environ = cls.save_env

    def setUp(self):
        """Before every test"""
        logging.debug("\n%s", "-" * 70)

    def check_command(self, cmd, exit_code=0):
        """Run shell command and check status"""
        logging.debug("Running: %s", cmd)
        commands = shlex.split(cmd)
        with subprocess.Popen(commands,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            stdout, stderr = process.communicate()
            self.assertEqual(
                process.returncode,
                exit_code, "\n" + "\n".join([
                    f"command: {cmd}",
                    f"stdout: {stdout.decode('utf-8')}",
                    f"stderr: {stderr.decode('utf-8')}"]))

    def grep_file(self, filename, regex):
        """Grep given filename"""
        pattern = re.compile(regex)
        logging.debug("RegEx = r'%s'", regex)
        with open(filename, "r") as fileobj:
            for line in fileobj:
                if pattern.search(line):
                    logging.debug(line)
                    return line
        self.fail(f"Could not find r'{regex}' in '{filename}'")
        return ""


class TestBasic(TestBase):
    """Basic tests"""

    def setUp(self):
        """Before every test: clean Bazel cache"""
        super().setUp()
        self.check_command("bazel clean")

    def test_bazel_test_all(self):
        """Test: bazel test ..."""
        self.check_command("bazel test ...")

    def test_bazel_build_pass(self):
        """Test: bazel build :test_pass"""
        self.check_command("bazel build :test_pass")

    def test_bazel_test_fail(self):
        """Test: bazel test :codechecker_fail"""
        self.check_command("bazel test :codechecker_fail", exit_code=3)
        logfile = os.path.join(
            self.BAZEL_BIN_DIR, "codechecker_fail", "codechecker.log")
        self.grep_file(logfile, r"clang-diagnostic-unused-variable\s+\|\s+MEDIUM\s+\|\s+1")
        self.grep_file(logfile, r"core.NullDereference\s+\|\s+HIGH\s+\|\s+1")
        self.grep_file(logfile, r"deadcode.DeadStores\s+\|\s+LOW\s+\|\s+1")
        self.grep_file(logfile, r"lib.cc\s+\|\s+3")

    def test_bazel_test_ctu(self):
        """Test: bazel test :codechecker_ctu"""
        self.check_command("bazel test :codechecker_ctu", exit_code=3)
        logfile = os.path.join(
            self.BAZEL_BIN_DIR, "codechecker_ctu", "codechecker.log")
        self.grep_file(logfile, "// CTU example")

    def test_bazel_build_fail(self):
        """Test: bazel build :test_fail"""
        self.check_command("bazel build :test_fail", exit_code=0)

    def test_bazel_compile_commands(self):
        """Test: bazel build --build_tag_filters=compile_commands ..."""
        self.check_command("bazel build --build_tag_filters=compile_commands ...")
        compile_commands = os.path.join(
            self.BAZEL_BIN_DIR, "compile_commands_pass", "compile_commands.json")
        self.grep_file(compile_commands, r"pass\.cc")
        self.grep_file(compile_commands, r"bin\/gcc")

    def test_bazel_aspect_clang_tidy_pass(self):
        """Test: bazel build :test_pass --aspects"""
        command = "bazel build :test_pass"
        command += " --aspects @bazel_codechecker//src:clang.bzl%clang_tidy_aspect"
        command += " --output_groups=report"
        self.check_command(command, exit_code=0)

    def test_bazel_aspect_clang_tidy_fail(self):
        """Test: bazel build :test_lib --aspects"""
        # NOTE: we should use :test_fail but transitive dependencies do not work
        command = "bazel build :test_lib"
        command += " --aspects @bazel_codechecker//src:clang.bzl%clang_tidy_aspect"
        command += " --output_groups=report"
        self.check_command(command, exit_code=1)

    def test_bazel_build_clang_tidy_pass(self):
        """Test: bazel build :clang_tidy_pass"""
        self.check_command("bazel build :clang_tidy_pass", exit_code=0)

    def test_bazel_build_clang_tidy_fail(self):
        """Test: bazel build :clang_tidy_fail"""
        self.check_command("bazel build :clang_tidy_fail", exit_code=1)

    def test_bazel_build_clang_analyze_pass(self):
        """Test: bazel build :clang_analyze_pass"""
        self.check_command("bazel build :clang_analyze_pass", exit_code=0)

    def test_bazel_build_clang_analyze_fail(self):
        """Test: bazel build :clang_analyze_fail"""
        self.check_command("bazel build :clang_analyze_fail", exit_code=1)

    def test_bazel_build_clang_ctu(self):
        """Test: bazel build :clang_ctu_pass :clang_ctu_fail"""
        self.check_command("bazel build :clang_ctu_pass :clang_ctu_fail", exit_code=0)

    def test_bazel_test_clang_ctu_pass(self):
        """Test: bazel test :clang_ctu_pass"""
        self.check_command("bazel test :clang_ctu_pass", exit_code=0)

    def test_bazel_test_clang_ctu_fail(self):
        """Test: bazel test :clang_ctu_fail"""
        self.check_command("bazel test :clang_ctu_fail", exit_code=3)
        logfile = os.path.join(
            self.BAZEL_TESTLOGS_DIR, "clang_ctu_fail", "test.log")
        self.grep_file(logfile, "// CTU example")

    def test_bazel_test_code_checker_pass(self):
        """Test: bazel test :code_checker_pass"""
        self.check_command("bazel test :code_checker_pass", exit_code=0)

    def test_bazel_test_code_checker_fail(self):
        """Test: bazel test :code_checker_fail"""
        self.check_command("bazel test :code_checker_fail", exit_code=3)
        logfile = os.path.join(
            self.BAZEL_TESTLOGS_DIR, "code_checker_fail", "test.log")
        self.grep_file(logfile, r"clang-diagnostic-unused-variable\s+\|\s+MEDIUM\s+\|\s+1")
        self.grep_file(logfile, r"core.NullDereference\s+\|\s+HIGH\s+\|\s+1")
        self.grep_file(logfile, r"deadcode.DeadStores\s+\|\s+LOW\s+\|\s+1")
        self.grep_file(logfile, r"lib.cc\s+\|\s+3")

    @unittest.skip("CodeChecker analyze --file --ctu does not work")
    def test_bazel_test_code_checker_ctu(self):
        """Test: bazel test :code_checker_ctu"""
        self.check_command("bazel test :code_checker_ctu", exit_code=3)
        logfile = os.path.join(
            self.BAZEL_TESTLOGS_DIR, "code_checker_ctu", "test.log")
        self.grep_file(logfile, "// CTU example")


def setup_logging():
    """Setup logging level for test execution"""
    # Enable debug logs for tests if "super verbose" flag is provided
    if "-vvv" in sys.argv:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[TEST] %(levelname)5s: %(message)s")


def main():
    """Run unittest"""
    setup_logging()
    logging.debug("Start testing...")
    unittest.main(buffer=True)


if __name__ == "__main__":
    main()
