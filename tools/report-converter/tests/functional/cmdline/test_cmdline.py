# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the report-converter tool.
"""


import subprocess
import unittest


class TestCmdline(unittest.TestCase):
    """ Simple tests to check report-converter command line. """

    def test_help(self):
        """ Get help for report-converter tool. """
        ret = subprocess.call(['report-converter', '--help'])
        self.assertEqual(0, ret)
