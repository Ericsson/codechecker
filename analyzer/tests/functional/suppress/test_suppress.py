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


import os
import inspect
import unittest

from libtest import env, codechecker


class TestSuppress(unittest.TestCase):
    """
    Test source-code level suppression data writing to suppress file.
    """

    def setUp(self):
        self._test_workspace = os.environ['TEST_WORKSPACE']

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._test_project_path = self._testproject_data['project_path']
        self._test_directory = os.path.dirname(os.path.abspath(inspect.getfile(
            inspect.currentframe())))

    def test_source_suppress_export(self):
        """
        Test exporting a source suppress comment automatically to file.
        """

        generated_file = os.path.join(self._test_workspace,
                                      "generated.suppress")
        skip_file = os.path.join(self._test_directory, "suppress_export.skip")

        extract_cmd = [env.codechecker_cmd(), 'parse',
                       os.path.join(self._test_workspace, "reports"),
                       "--suppress", generated_file,
                       "--export-source-suppress", "--ignore", skip_file]

        _, _, ret = codechecker.call_command(
            extract_cmd, self._test_project_path,
            env.test_env(self._test_directory))
        self.assertEqual(ret, 2, "Failed to generate suppress file.")

        with open(generated_file, 'r',
                  encoding='utf-8', errors='ignore') as generated:
            expected_file = os.path.join(self._test_directory,
                                         "suppress.expected")
            with open(expected_file, 'r', encoding='utf-8',
                      errors='ignore') as expected:
                generated_content = generated.read()
                expected_content = expected.read()
                print("generated")
                print(generated_content)
                print("expected")
                print(expected_content)

                diff = set(expected_content).symmetric_difference(
                           generated_content)
                print("difference")
                {print(elem) for elem in diff}
                self.assertEqual(len(diff),
                                 0,
                                 "The generated suppress file does not "
                                 "look like what was expected")

    def test_doubled_suppress(self):
        """
        Test to catch repeated suppress comments with same bug.
        """

        skip_file = os.path.join(self._test_directory,
                                 "duplicated_suppress.skip")

        cmd = [env.codechecker_cmd(), 'parse',
               os.path.join(self._test_workspace, "reports"),
               "--ignore", skip_file]

        _, _, ret = codechecker.call_command(
            cmd, self._test_project_path,
            env.test_env(self._test_workspace))
        self.assertEqual(ret, 1, "Repeated suppress comment not recognized.")

    def test_doubled_suppress_by_all(self):
        """
        Test to catch multiple suppress comments in a line when "all"
        is one of them.
        """

        skip_file = os.path.join(self._test_directory, "suppress_by_all.skip")

        cmd = [env.codechecker_cmd(), 'parse',
               os.path.join(self._test_workspace, "reports"),
               "--ignore", skip_file]

        _, _, ret = codechecker.call_command(
            cmd, self._test_project_path,
            env.test_env(self._test_workspace))
        self.assertEqual(ret, 1, "Already covered suppress comment not "
                         "recognized.")

    def test_doubled_suppress_by_all_in_two_lines(self):
        """
        Test to catch unnecessary suppress comment that was covered by a
        suppress all comment in the previous line.
        """

        skip_file = os.path.join(self._test_directory,
                                 "suppress_by_all_in_two_lines.skip")

        cmd = [env.codechecker_cmd(), 'parse',
               os.path.join(self._test_workspace, "reports"),
               "--ignore", skip_file]

        _, _, ret = codechecker.call_command(
            cmd, self._test_project_path,
            env.test_env(self._test_workspace))
        self.assertEqual(ret, 1, "Already covered suppress comment not "
                         "recognized.")

    def test_confirmed_already_suppressed(self):
        """
        Test to catch unnecessary confirmed comment that was covered by a
        suppress all comment in the previous line.
        """

        skip_file = os.path.join(self._test_directory,
                                 "suppress_already_confirmed.skip")

        cmd = [env.codechecker_cmd(), 'parse',
               os.path.join(self._test_workspace, "reports"),
               "--ignore", skip_file]

        _, _, ret = codechecker.call_command(
            cmd, self._test_project_path,
            env.test_env(self._test_workspace))
        self.assertEqual(ret, 1, "Already suppressed comment must not be "
                         "confirmed.")

    def test_suppress_with_no_bug_is_ok(self):
        """
        Test that the suppress comment that suppresses non existent bug does
        not cause fail.
        """

        skip_file = os.path.join(self._test_directory,
                                 "suppress_without_bug.skip")

        cmd = [env.codechecker_cmd(), 'parse',
               os.path.join(self._test_workspace, "reports"),
               "--ignore", skip_file]

        _, _, ret = codechecker.call_command(
            cmd, self._test_project_path,
            env.test_env(self._test_workspace))
        self.assertEqual(ret, 0, "Suppress without existent bug causes error.")
