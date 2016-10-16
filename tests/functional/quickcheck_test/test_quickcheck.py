# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""This module tests the CodeChecker quickcheck feature."""

import glob
import os
import subprocess
import unittest

from subprocess import CalledProcessError


class QuickCheckTestCase(unittest.TestCase):
    """This class tests the CodeChecker quickcheck feature."""

    @classmethod
    def setup_class(cls):
        """Setup the class."""
        cls.package_dir = \
            os.path.realpath(os.environ.get('TEST_CODECHECKER_DIR'))

        # Put CodeChecker/bin to PATH so CodeChecker command becomes available.
        cls.env = os.environ.copy()
        cls.env['PATH'] = \
            os.path.join(cls.package_dir, 'bin') + ':' + cls.env['PATH']

        cls.test_dir = os.path.join(
            os.path.dirname(__file__), 'quickcheck_test_files')

        # Change working dir to testfile dir so CodeChecker can be run easily.
        os.chdir(cls.test_dir)

    def __check_one_file(self, path):
        """Test quickcheck output on a ".output" file.

        The first line of the '.output' file contains the build command of the
        corresponding test file.
        The second line is to be omitted.
        From the third line onward, the file contains the output of the
        build command found in the first line.
        """
        with open(path, 'r') as ofile:
            lines = ofile.readlines()

        command, correct_output = (lines[0].strip(), ''.join(lines[2:]))

        try:
            output = subprocess.check_output(
                ['bash', '-c', command], env=self.env, cwd=self.test_dir)

            self.assertEqual(output, correct_output)
            return 0
        except CalledProcessError as cerr:
            print("Failed to run: " + ' '.join(cerr.cmd))
            print(cerr.output)
            return cerr.returncode

    def test_quickcheck_files(self):
        """Iterate over the test directory and run all tests in it."""
        for ofile in glob.glob(os.path.join(self.test_dir, '*.output')):
            self.assertEqual(self.__check_one_file(ofile), 0)
