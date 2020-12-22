# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Test Store handler features.  """


import os
import unittest

from codechecker_common import plist_parser
from codechecker_report_hash.hash import get_report_path_hash


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
        files, reports = plist_parser.parse_plist_file(clang50_trunk_plist,
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
                'acb1d3dc1459f681bd3c743e6c015b37',
            '8714f42d8328bc78d5d7bff6ced918cc':
                'dcaaf2905d607a16e3fa330edb8e9f89',
            'a6d3464f8aab9eb31a8ea7e167e84322':
                'd089a50f34051c68c7bb4c5ac2c4c5d5'
        }

        for report in reports:
            path_hash = get_report_path_hash(report)
            bug_hash = report.main['issue_hash_content_of_line_in_context']
            self.assertEqual(path_hash, report_hash_to_path_hash[bug_hash])
