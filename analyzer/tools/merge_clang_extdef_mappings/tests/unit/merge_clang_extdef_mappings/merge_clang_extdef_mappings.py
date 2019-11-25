# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import os
import unittest

from codechecker_merge_clang_extdef_mappings import merge_clang_extdef_mappings


class MergeClangExtdefMappingsTest(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        """ Initialize test files. """
        self.test_workspace = os.environ['TEST_WORKSPACE']

        self.extdef_maps_dir = os.path.join(self.test_workspace,
                                            "extdef_maps")

        if not os.path.exists(self.extdef_maps_dir):
            os.makedirs(self.extdef_maps_dir)

        self.extdef_map_1_lines = ["c:@F@f# path/to/file.cpp.ast",
                                   "c:@F@g# path/to/file.cpp.ast",
                                   "c:@F@both# path/to/file.cpp.ast"]

        extdef_map_file_1 = os.path.join(self.extdef_maps_dir,
                                         'externalDefMap1.txt')
        with open(extdef_map_file_1, 'w',
                  encoding='utf-8', errors='ignore') as map_f:
            map_f.write('\n'.join(self.extdef_map_1_lines))

        self.extdef_map_2_lines = ["c:@F@main# path/to/file2.cpp.ast",
                                   "c:@F@h# path/to/file2.cpp.ast",
                                   "c:@F@both# path/to/file2.cpp.ast"]

        extdef_map_file_2 = os.path.join(self.extdef_maps_dir,
                                         'externalDefMap2.txt')
        with open(extdef_map_file_2, 'w',
                  encoding='utf-8', errors='ignore') as map_f:
            map_f.write('\n'.join(self.extdef_map_2_lines))

    def test_merge_clang_extdef_mappings(self):
        """ Test merging multiple func map files. """

        output_file = os.path.join(self.test_workspace, 'externalDefMap.txt')
        merge_clang_extdef_mappings.merge(self.extdef_maps_dir, output_file)

        with open(output_file, 'r',
                  encoding='utf-8', errors='ignore') as o_file:
            lines = o_file.read().split('\n')

        expected_lines = ["c:@F@f# path/to/file.cpp.ast",
                          "c:@F@g# path/to/file.cpp.ast",
                          "c:@F@main# path/to/file2.cpp.ast",
                          "c:@F@h# path/to/file2.cpp.ast"]
        for expected_line in expected_lines:
            self.assertTrue(expected_line in lines)
