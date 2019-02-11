# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------
""" Test Store handler features.  """
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

from libcodechecker import plist_parser
from libcodechecker.report import get_report_path_hash


class ReportPathHashHandler(unittest.TestCase):
    """
    Test report path hash generation handler features.
    """

    @classmethod
    def setup_class(cls):
        # Already generated plist files for the tests.
        cls.__this_dir = os.path.dirname(__file__)
        cls.__plist_test_files = os.path.join(
            cls.__this_dir, 'plist_test_files')

    def test_report_path_hash_generation(self):
        """
        Test report path hash generation.
        """
        clang50_trunk_plist = os.path.join(
            self.__plist_test_files, 'clang-5.0-trunk.plist')
        files, reports = plist_parser.parse_plist(clang50_trunk_plist, None,
                                                  False)
        self.assertEqual(len(reports), 3)

        # Generate dummy file_ids which should come from the database.
        file_ids = {}
        for i, file_name in enumerate(files, 1):
            file_ids[file_name] = i

        msg = "This test is prepared to handle 3 reports."
        self.assertEqual(len(reports), 3, msg)

        report_hash_to_path_hash = {
            '79e31a6ba028f0b7d9779faf4a6cb9cf':
                'c473c1a55df72ea4c6e055e18370ac65',
            '8714f42d8328bc78d5d7bff6ced918cc':
                '94f2a6eee8af6462a810218dff35056a',
            'a6d3464f8aab9eb31a8ea7e167e84322':
                '11f410136724cf43c63526841007897e'
        }

        for report in reports:
            path_hash = get_report_path_hash(report, files)
            bug_hash = report.main['issue_hash_content_of_line_in_context']
            self.assertEqual(path_hash, report_hash_to_path_hash[bug_hash])
