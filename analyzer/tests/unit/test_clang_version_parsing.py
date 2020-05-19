# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test the CTU autodetection feature, which determines the mapping tool and
the mapping file name used for CTU analysis. """


import unittest
import os

from codechecker_analyzer.analyzers.clangsa import version


OLD_PWD = None


def setup_module():
    """Change to the directory with sample version outputs."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'ctu_autodetection_test_files'))


def teardown_module():
    """Restore the current working directory."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class CTUAutodetectionVersionParsingTest(unittest.TestCase):
    """
    Test the parsing of various possible version strings, which clang binaries
    can produce.
    """

    def test_empty_version_string_is_rejected(self):
        """
        Test that the empty stirng is not a valid version-string.
        """

        parser = version.ClangVersionInfoParser()
        version_info = parser.parse('')

        self.assertFalse(version_info, False)

    def test_built_from_source_clang_7(self):
        """
        Test that source-built clang release_70 version string is parsed
        correctly.
        """

        with open('clang_7_src_version_output',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.ClangVersionInfoParser()
        version_info = parser.parse(version_string)

        self.assertIsNot(version_info, False)
        self.assertEqual(version_info.major_version, 7)
        self.assertEqual(version_info.minor_version, 1)
        self.assertEqual(version_info.patch_version, 0)
        self.assertEqual(version_info.installed_dir, '/path/to/clang/bin')

    def test_built_from_source_clang_8(self):
        """
        Test that source-built clang release_80 version string is parsed
        correctly.
        """

        with open('clang_8_src_version_output',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.ClangVersionInfoParser()
        version_info = parser.parse(version_string)

        self.assertIsNot(version_info, False)
        self.assertEqual(version_info.major_version, 8)
        self.assertEqual(version_info.minor_version, 0)
        self.assertEqual(version_info.patch_version, 1)
        self.assertEqual(version_info.installed_dir, '/path/to/clang/bin')

    def test_binary_distribution_clang_7(self):
        """
        Test that binary distribution of clang 7 version string is parsed
        correctly.
        """

        with open('clang_7_bin_dist_version_output',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.ClangVersionInfoParser()
        version_info = parser.parse(version_string)

        self.assertIsNot(version_info, False)
        self.assertEqual(version_info.major_version, 7)
        self.assertEqual(version_info.minor_version, 0)
        self.assertEqual(version_info.patch_version, 0)
        self.assertEqual(version_info.installed_dir, '/path/to/clang/bin')

    def test_built_from_monorepo_source_clang_9(self):
        """
        Test that monorepo source-built clang 9 master string is parsed
        correctly.
        """

        with open('clang_9_monorepo_src_version_output',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.ClangVersionInfoParser()
        version_info = parser.parse(version_string)

        self.assertIsNot(version_info, False)
        self.assertEqual(version_info.major_version, 9)
        self.assertEqual(version_info.minor_version, 0)
        self.assertEqual(version_info.patch_version, 0)
        self.assertEqual(version_info.installed_dir, '/path/to/clang/bin')

    def test_built_from_gcc(self):
        """ Test if parsing a gcc version info returns False. """

        with open('gcc_version',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.ClangVersionInfoParser()
        version_info = parser.parse(version_string)
        self.assertIs(version_info, False)
