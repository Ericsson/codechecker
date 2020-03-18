# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the the commandline tool ccdb-tool.
"""


import subprocess
import unittest


class TestToolAvailability(unittest.TestCase):
    """ The tool should be available with the name ccdb-tool. """

    def test_help(self):
        """ Get help for ccdb-tool. """
        ret = subprocess.call(['ccdb-tool', '--help'])
        self.assertEqual(0, ret)
