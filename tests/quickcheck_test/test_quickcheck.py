# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""Doc."""

import glob
import os
import subprocess
import unittest


class QuickCheckTestCase(unittest.TestCase):
    """DOC."""

    @classmethod
    def setup_class(cls):
        """DOC."""
        cls.package_dir = \
            os.path.realpath(os.environ.get('TEST_CODECHECKER_DIR'))

        cls.env = os.environ
        cls.env['PATH'] = \
            os.path.join(cls.package_dir, 'bin') + ':' + cls.env['PATH']

        cls.test_dir = os.path.join(
            os.path.dirname(__file__), 'quickcheck_test_files')

        os.chdir(cls.test_dir)

    def __check_one_file(self, path):
        """Test quickcheck output on a ".output" file."""
        with open(path, 'r') as ofile:
            lines = ofile.readlines()

        options, correct_output = (lines[0].strip(), ''.join(lines[2:]))

        command = 'CodeChecker quickcheck --analyzers clangsa ' + options

        output = subprocess.check_output(
            ['bash', '-c', command], env=self.env, cwd=self.test_dir)

        print path
        # print correct_output

        self.assertEqual(output, correct_output)

    def test_quickcheck_files(self):
        """Iterate over the test directory and run all tests in it."""
        for ofile in glob.glob(self.test_dir + os.sep + '*.output'):
            self.__check_one_file(ofile)
