# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test source-code level suppression data writing to suppress file.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

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
            env=env)
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
        self.assertEqual(ret, 0, "Failed to generate suppress file.")

        with open(generated_file, 'r') as generated:
            with open(os.path.join(self._test_project_path,
                      "suppress.expected"), 'r') as expected:
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
