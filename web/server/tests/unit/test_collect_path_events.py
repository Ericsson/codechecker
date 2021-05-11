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

from codechecker_api.codeCheckerDBAccess_v6 import ttypes

from codechecker_common import plist_parser

from codechecker_server.api.mass_store_run import collect_paths_events


class CollectPathEventsTest(unittest.TestCase):
    """
    Test collecting path events.
    """

    @classmethod
    def setup_class(cls):
        # Already generated plist files for the tests.
        cls.__this_dir = os.path.dirname(__file__)
        cls.__plist_test_files = os.path.join(
            cls.__this_dir, 'plist_test_files')

    def test_collect_path_events(self):
        """
        Test path event collect before store.
        """
        clang50_trunk_plist = os.path.join(
            self.__plist_test_files, 'clang-5.0-trunk.plist')
        files, reports = plist_parser.parse_plist_file(clang50_trunk_plist,
                                                       False)
        self.assertEqual(len(reports), 3)

        # Generate dummy file_ids which should come from the database.
        file_ids = {}
        for i, file_name in files.items():
            file_ids[file_name] = i + 1

        msg = "This test is prepared to handle 3 reports."
        self.assertEqual(len(reports), 3, msg)

        report1_path = [
            ttypes.BugPathPos(startLine=19, filePath=None, endCol=7,
                              startCol=5, endLine=19, fileId=1),
            ttypes.BugPathPos(startLine=20, filePath=None, endCol=7,
                              startCol=5, endLine=20, fileId=1),
            ttypes.BugPathPos(startLine=21, filePath=None, endCol=13,
                              startCol=5, endLine=21, fileId=1),
            ttypes.BugPathPos(startLine=7, filePath=None, endCol=7,
                              startCol=5, endLine=7, fileId=1),
            ttypes.BugPathPos(startLine=8, filePath=None, endCol=6,
                              startCol=5, endLine=8, fileId=1),
            ttypes.BugPathPos(startLine=8, filePath=None, endCol=25,
                              startCol=22, endLine=8, fileId=1),
            ttypes.BugPathPos(startLine=8, filePath=None, endCol=20,
                              startCol=10, endLine=8, fileId=1),
            ttypes.BugPathPos(startLine=7, filePath=None, endCol=14,
                              startCol=14, endLine=7, fileId=2)
        ]
        report1_events = [
            ttypes.BugPathEvent(startLine=20, filePath=None, endCol=12,
                                startCol=5, msg="'base' initialized to 0",
                                endLine=20, fileId=1),
            ttypes.BugPathEvent(startLine=21, filePath=None, endCol=18,
                                startCol=15,
                                msg="Passing the value 0 via "
                                "1st parameter 'base'",
                                endLine=21, fileId=1),
            ttypes.BugPathEvent(startLine=21, filePath=None, endCol=19,
                                startCol=5, msg="Calling 'test_func'",
                                endLine=21, fileId=1),
            ttypes.BugPathEvent(startLine=6, filePath=None, endCol=1,
                                startCol=1, msg="Entered call from 'main'",
                                endLine=6, fileId=1),
            ttypes.BugPathEvent(startLine=8, filePath=None, endCol=25,
                                startCol=22,
                                msg="Passing the value 0 via "
                                "1st parameter 'num'", endLine=8, fileId=1),
            ttypes.BugPathEvent(startLine=8, filePath=None, endCol=26,
                                startCol=10, msg="Calling 'generate_id'",
                                endLine=8, fileId=1),
            ttypes.BugPathEvent(startLine=6, filePath=None, endCol=1,
                                startCol=1,
                                msg="Entered call from 'test_func'",
                                endLine=6, fileId=2),
            ttypes.BugPathEvent(startLine=7, filePath=None, endCol=17,
                                startCol=12, msg='Division by zero',
                                endLine=7, fileId=2)
        ]

        path1, events1, _ = collect_paths_events(reports[0], file_ids, files)

        self.assertEqual(path1, report1_path)
        self.assertEqual(events1, report1_events)

        report2_path = []
        report2_events = [
            ttypes.BugPathEvent(startLine=8, filePath=None, endCol=26,
                                startCol=10,
                                msg="Value stored to 'id' is ""never read",
                                endLine=8, fileId=1)
        ]

        path2, events2, _ = collect_paths_events(reports[1], file_ids, files)

        self.assertEqual(path2, report2_path)
        self.assertEqual(events2, report2_events)

        report3_path = [
            ttypes.BugPathPos(startLine=14, filePath=None, endCol=6,
                              startCol=3, endLine=14, fileId=1),
            ttypes.BugPathPos(startLine=15, filePath=None, endCol=3,
                              startCol=3, endLine=15, fileId=1),
            ttypes.BugPathPos(startLine=16, filePath=None, endCol=1,
                              startCol=1, endLine=16, fileId=1)
        ]
        report3_events = [
            ttypes.BugPathEvent(startLine=14, filePath=None, endCol=29,
                                startCol=3,
                                msg="Address of stack memory associated"
                                    " with local variable 'str'"
                                    " is still referred to by the global "
                                    "variable 'p' upon returning to the "
                                    "caller.  This will be a dangling "
                                    "reference",
                                endLine=14, fileId=1)
        ]

        path, events, _ = collect_paths_events(reports[2], file_ids, files)

        self.assertEqual(path, report3_path)
        self.assertEqual(events, report3_events)
