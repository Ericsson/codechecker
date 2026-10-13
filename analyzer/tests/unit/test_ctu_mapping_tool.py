# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test the detection of the CTU mapping tool of Clang. """


import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from semver.version import Version

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA


class CtuMappingToolTest(unittest.TestCase):
    """
    Test that ClangSA.ctu_mapping() finds the mapping tool next to the
    analyzer binary, with and without the Windows executable suffix.
    """

    def setUp(self):
        self.bin_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.bin_dir)

    def __touch(self, file_name):
        path = os.path.join(self.bin_dir, file_name)
        with open(path, 'w', encoding='utf-8'):
            pass
        return path

    def __ctu_mapping(self, platform, clang_name, version):
        clang = self.__touch(clang_name)

        with patch.object(ClangSA, 'analyzer_binary',
                          return_value=clang), \
                patch.object(ClangSA, 'get_binary_version',
                             return_value=version), \
                patch('sys.platform', platform):
            return ClangSA.ctu_mapping()

    def test_extdef_mapping(self):
        tool = self.__touch('clang-extdef-mapping')

        self.assertEqual(
            self.__ctu_mapping('linux', 'clang', Version(18, 1, 8)),
            (tool, 'externalDefMap.txt'))

    def test_extdef_mapping_windows(self):
        tool = self.__touch('clang-extdef-mapping.exe')

        self.assertEqual(
            self.__ctu_mapping('win32', 'clang.exe', Version(18, 1, 8)),
            (tool, 'externalDefMap.txt'))

    def test_postfixed_extdef_mapping(self):
        tool = self.__touch('clang-extdef-mapping-18')

        self.assertEqual(
            self.__ctu_mapping('linux', 'clang-18', Version(18, 1, 8)),
            (tool, 'externalDefMap.txt'))

    def test_postfixed_extdef_mapping_windows(self):
        tool = self.__touch('clang-extdef-mapping-18.exe')

        self.assertEqual(
            self.__ctu_mapping('win32', 'clang.exe', Version(18, 1, 8)),
            (tool, 'externalDefMap.txt'))

    def test_dotted_clang_name(self):
        """
        A version number in the name of the analyzer binary must not be
        taken as a file name suffix.
        """
        tool = self.__touch('clang-extdef-mapping')

        self.assertEqual(
            self.__ctu_mapping('linux', 'clang-18.1', Version(18, 1, 8)),
            (tool, 'externalDefMap.txt'))

    def test_func_mapping(self):
        tool = self.__touch('clang-func-mapping')

        self.assertEqual(
            self.__ctu_mapping('linux', 'clang', Version(7, 0, 1)),
            (tool, 'externalFnMap.txt'))

    def test_func_mapping_windows(self):
        tool = self.__touch('clang-func-mapping.exe')

        self.assertEqual(
            self.__ctu_mapping('win32', 'clang.exe', Version(7, 0, 1)),
            (tool, 'externalFnMap.txt'))

    def test_missing_tool(self):
        self.__touch('clang-func-mapping')

        self.assertEqual(
            self.__ctu_mapping('linux', 'clang', Version(18, 1, 8)),
            (None, None))

    def test_missing_tool_windows(self):
        # Without the '.exe' suffix the file is not the mapping tool.
        self.__touch('clang-extdef-mapping')

        self.assertEqual(
            self.__ctu_mapping('win32', 'clang.exe', Version(18, 1, 8)),
            (None, None))

    def test_no_clang_version(self):
        self.__touch('clang-extdef-mapping')

        self.assertEqual(
            self.__ctu_mapping('linux', 'clang', None),
            (None, None))
