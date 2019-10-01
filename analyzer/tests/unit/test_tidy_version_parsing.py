
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test the clang-tidy version parsing functions """


import unittest
import os

from codechecker_analyzer.analyzers.clangtidy import version


OLD_PWD = None


def setup_module():
    """Change to the directory with sample version outputs."""
    global OLD_PWD
    OLD_PWD = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__),
                          'tidy_version_output'))


def teardown_module():
    """Restore the current working directory."""
    global OLD_PWD
    os.chdir(OLD_PWD)


class ClangTidyVersionParsingTest(unittest.TestCase):
    """
    """

    def test_empty_version_string_is_rejected(self):
        """
        Test that the empty string is not a valid version string.
        """

        parser = version.TidyVersionInfoParser()
        version_info = parser.parse('')

        self.assertFalse(version_info, False)

    def test_tidy_release_v9(self):
        """
        Test that clang tidy release version 9.0.0 string is parsed correctly.
        """
        with open('clang-tidy-v9.0.0.output',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.TidyVersionInfoParser()
        version_info = parser.parse(version_string)

        self.assertIsNot(version_info, False)
        self.assertEqual(version_info.major_version, 9)
        self.assertEqual(version_info.minor_version, 0)
        self.assertEqual(version_info.patch_version, 0)

    def test_tidy_v11_source(self):
        """
        Test that clang tidy release version 11.0.0 (built from source)
        string is parsed correctly.
        """
        with open('clang-tidy-v11.0.0git.output',
                  encoding="utf-8", errors="ignore") as version_output:
            version_string = version_output.read()

        parser = version.TidyVersionInfoParser()
        version_info = parser.parse(version_string)

        self.assertIsNot(version_info, False)
        self.assertEqual(version_info.major_version, 11)
        self.assertEqual(version_info.minor_version, 0)
        self.assertEqual(version_info.patch_version, 0)
