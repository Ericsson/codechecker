# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the warning-to-plist tool.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import subprocess
import unittest


def run_cmd(cmd, env=None):
    print(cmd)
    proc = subprocess.Popen(cmd,
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out, err = proc.communicate()
    print(out)
    return proc.returncode, out, err


class TestCmdline(unittest.TestCase):
    """ Simple tests to check warning-to-plist command line. """

    def test_help(self):
        """ Get help for warning-to-plist tool. """
        cmd_help = ['warning-to-plist', '--help']
        self.assertEqual(0, run_cmd(cmd_help)[0])
