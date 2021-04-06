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
import shlex
import subprocess
import unittest

from libtest import env


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
    except subprocess.CalledProcessError as cerr:
        print("Failed to call:\n" + ' '.join(cerr.cmd))
        return cerr.returncode


class TestSuppress(unittest.TestCase):
    """
    Test source-code level suppression data writing to suppress file.
    """

    def setUp(self):
        self._test_workspace = os.environ['TEST_WORKSPACE']

        self._testproject_data = env.setup_test_proj_cfg(self._test_workspace)
        self.assertIsNotNone(self._testproject_data)

        self._test_project_path = self._testproject_data['project_path']

    def test_source_suppress_export(self):
        """
        Test exporting a source suppress comment automatically to file.
        """

        generated_file = os.path.join(self._test_workspace,
                                      "generated.suppress")

        extract_cmd = ['CodeChecker', 'parse',
                       os.path.join(self._test_workspace, "reports"),
                       "--suppress", generated_file,
                       "--export-source-suppress",
                       "--verbose", "debug"]

        ret = call_cmd(extract_cmd,
                       self._test_project_path,
                       env.test_env(self._test_workspace))
        self.assertEqual(ret, 2, "Failed to generate suppress file.")

        with open(generated_file, 'r',
                  encoding='utf-8', errors='ignore') as generated:
            expected_file = os.path.join(self._test_project_path,
                                         "suppress.expected")
            with open(expected_file, 'r', encoding='utf-8',
                      errors='ignore') as expected:
                generated_content = generated.read()
                expected_content = expected.read()
                print("generated")
                print(generated_content)
                print("expected")
                print(expected_content)

                diff = set(expected_content).difference(generated_content)
                self.assertEqual(len(diff),
                                 0,
                                 "The generated suppress file does not "
                                 "look like what was expected")
