# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""This module tests the CodeChecker command line."""

import os
import subprocess
import unittest

from nose.tools import assert_equals


class CmdLineTestCase(unittest.TestCase):
    """This class tests the CodeChecker command line features."""

    @classmethod
    def setup_class(cls):
        """Setup the class."""
        cls.package_dir = \
            os.path.realpath(os.environ.get('CC_PACKAGE'))

        ''' Put CodeChecker/bin to PATH so CodeChecker
        command becomes available in the environment used for testing. '''
        cls.env = os.environ.copy()
        cls.env['PATH'] = \
            os.path.join(cls.package_dir, 'bin') + ':' + cls.env['PATH']

    def test_cmdline_help(self):
        """Check if calling the help for the build package
        works poperly. No exceptions."""

        help_cmd = ['CodeChecker', '--help']

        proc = subprocess.Popen(help_cmd,
                                stdout=subprocess.PIPE,
                                env=self.env)

        out, _ = proc.communicate()
        print(out)
        assert_equals(0, proc.returncode)
