# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Unit tests for trimming white spaces. """

import unittest

from libcodechecker.util import get_new_line_col_without_whitespace


class ReportLineTest(unittest.TestCase):
    """
    Testing string by removing white spaces.
    """

    def __check_trim(self, content, col, expected):
        params = get_new_line_col_without_whitespace(content, col)
        self.assertEqual(params[0], expected[0])
        self.assertEqual(params[1], expected[1])

    def test_report_line_trailing_whitespace(self):
        """
        Test trailing white spaces.
        """

        self.__check_trim("foo", 0, ("foo", 0))
        self.__check_trim(" foo", 0, ("foo", 0))
        self.__check_trim("   foo  ", 0, ("foo", 0))

    def test_report_line_inner_whitespace(self):
        """
        Test white spaces inside a string.
        """

        self.__check_trim("foo;  bar", 0, ("foo;bar", 0))
        self.__check_trim("  foo; bar  ", 0, ("foo;bar", 0))
        self.__check_trim("  foo;   bar  ", 0, ("foo;bar", 0))
        self.__check_trim("  foo  ;   bar  ", 0, ("foo;bar", 0))

    def test_report_line_column(self):
        """
        Test new line column by removing white spaces.
        """
        self.__check_trim("   foo    ", 4, ("foo", 1))

        self.__check_trim("  foo; foo2  ", 3, ("foo;foo2", 1))
        self.__check_trim("  foo;  foo2  ", 3, ("foo;foo2", 1))
        self.__check_trim("  foo;  foo2  ", 9, ("foo;foo2", 5))

        self.__check_trim("f ( 2 ); ", 1, ("f(2);", 1))
        self.__check_trim("  f ( 2 );", 3, ("f(2);", 1))
        self.__check_trim("  f  (  2  )  ;  ", 3, ("f(2);", 1))
