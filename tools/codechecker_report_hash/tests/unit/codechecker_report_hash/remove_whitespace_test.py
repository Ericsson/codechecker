# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
""" Test remove whitespace.  """

import unittest

from codechecker_report_hash.hash import _remove_whitespace


class RemoveWhitespaceTest(unittest.TestCase):
    """ Whitespace removal tests. """

    def test_remove_empty(self):
        """
        empty line
        """
        result, cnt = _remove_whitespace("", 0)
        self.assertEqual(result, "")
        self.assertEqual(cnt, 0)

    def test_being_space(self):
        source_line = "     int main()"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain()")
        self.assertEqual(cnt, 4)

    def test_multiple_space_inbetween(self):
        source_line = "   int   main()"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain()")
        self.assertEqual(cnt, 4)

    def test_tab_space_mix_inbetween(self):
        source_line = "	int	 main(){}"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain(){}")
        self.assertEqual(cnt, 7)

    def test_multiple_tab_and_space_inbetween(self):
        source_line = "			int	 main()"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain()")
        self.assertEqual(cnt, 5)

    def test_multiple_tab_and_space_col_in_space(self):
        """
        column number points to a section with whitespaces
        """
        source_line = "	  	int	     	 main()"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain()")
        self.assertEqual(cnt, 3)

    def test_no_whitespace_on_line_start(self):
        source_line = "int	      main()"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain()")
        self.assertEqual(cnt, 3)

    def test_no_extra_space(self):
        source_line = "int main(){}"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain(){}")
        self.assertEqual(cnt, 9)

    def test_tab_inline_empty(self):
        source_line = "int	main(){}"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmain(){}")
        self.assertEqual(cnt, 9)

    def test_nonascii(self):
        """
        non ascii character
        """
        source_line = "int	máin(){}"
        result, cnt = _remove_whitespace(source_line, 10)
        self.assertEqual(result, "intmáin(){}")
        self.assertEqual(cnt, 9)
