# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
"""
Test source-code level suppression data writing to suppress file.
"""

from subprocess import CalledProcessError
import os
import shlex
import subprocess
import unittest

from libtest import env


class TestSuppress(unittest.TestCase):
    """
    Test source-code level suppression data writing to suppress file.
    """

    def setUp(self):
        self.test_workspace = os.environ['TEST_WORKSPACE']
        self.test_dir = os.path.join(
            os.path.dirname(__file__), "test_files")

    def test_source_suppress_export(self):
        """
        Test exporting a source suppress comment automatically to file.
        """

        def __call(command):
            try:
                print(' '.join(command))
                proc = subprocess.Popen(shlex.split(' '.join(command)),
                                        cwd=self.test_dir,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        env=env.test_env())
                out, err = proc.communicate()
                print(out)
                print(err)
                return 0
            except CalledProcessError as cerr:
                print("Failed to call:\n" + ' '.join(cerr.cmd))
                return cerr.returncode

        analyze_cmd = ['CodeChecker', 'analyze',
                       os.path.join(self.test_dir, "build.json"),
                       "--output", os.path.join(self.test_workspace, "reports")
                       ]
        ret = __call(analyze_cmd)
        self.assertEqual(ret, 0, "Couldn't create analysis of test project.")

        generated_file = os.path.join(self.test_workspace,
                                      "generated.suppress")

        extract_cmd = ['CodeChecker', 'parse',
                       os.path.join(self.test_workspace, "reports"),
                       "--suppress", generated_file,
                       "--export-source-suppress"
                       ]
        __call(extract_cmd)
        self.assertEqual(ret, 0, "Failed to generate suppress file.")

        with open(generated_file, 'r') as generated:
            with open(os.path.join(self.test_dir, "expected.suppress"),
                      'r') as expected:
                self.assertEqual(generated.read().strip(),
                                 expected.read().strip(),
                                 "The generated suppress file does not "
                                 "look like what was expected.")
