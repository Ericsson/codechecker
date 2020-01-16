# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
This module tests the report-converter tool.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import subprocess
import unittest


class TestCmdline(unittest.TestCase):
    """ Simple tests to check report-converter command line. """

    def test_help(self):
        """ Get help for report-converter tool. """
        ret = subprocess.call(['report-converter', '--help'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(0, ret)
