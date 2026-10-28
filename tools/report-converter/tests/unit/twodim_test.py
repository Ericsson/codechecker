# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""Tests for the plain text table rendering of the twodim module."""

import os
import unittest

from unittest import mock

from codechecker_report_converter import twodim


class TwodimTableTest(unittest.TestCase):
    """
    Test that the table output adapts to the character set of the effective
    locale.
    """

    HEAD = ['Kind', 'Version']
    ROWS = [['Base package version', '6.29.0']]

    def to_table_with_locale(self, **locale_vars) -> str:
        """ Render a table with only the given locale variables set. """
        env = {k: v for k, v in os.environ.items()
               if k not in ('LC_ALL', 'LC_CTYPE', 'LANG')}
        env.update({k: v for k, v in locale_vars.items() if v is not None})

        with mock.patch.dict(os.environ, env, clear=True):
            return twodim.to_table([self.HEAD] + self.ROWS)

    def test_utf8_locale_keeps_box_drawing(self):
        """ A UTF-8 locale keeps the box-drawing table style. """
        for locale in ('en_US.UTF-8', 'C.UTF-8', 'en_US.utf8',
                       'en_US.UTF-8@euro'):
            table = self.to_table_with_locale(LC_ALL=locale)
            self.assertIn('│', table, locale)
            self.assertNotIn('+', table, locale)

    def test_non_utf8_locale_degrades_to_ascii(self):
        """
        Locales without UTF-8 character set degrade to an ASCII-only table.
        """
        for locale in ('C', 'POSIX', 'en_US.ISO-8859-1', 'en_US'):
            table = self.to_table_with_locale(LC_ALL=locale)
            self.assertIn('|', table, locale)
            self.assertIn('+', table, locale)
            self.assertNotIn('│', table, locale)

    def test_unset_locale_degrades_to_ascii(self):
        """
        An unspecified locale, which is common in CI pipelines, degrades to
        an ASCII-only table.
        """
        table = self.to_table_with_locale(
            LC_ALL=None, LC_CTYPE=None, LANG=None)
        self.assertIn('+', table)
        self.assertNotIn('│', table)

    def test_locale_precedence(self):
        """
        LC_ALL overrides LC_CTYPE, which overrides LANG, as required by
        POSIX.
        """
        table = self.to_table_with_locale(
            LC_ALL='en_US.UTF-8', LC_CTYPE='C', LANG='C')
        self.assertIn('│', table)

        table = self.to_table_with_locale(
            LC_ALL=None, LC_CTYPE='C', LANG='en_US.UTF-8')
        self.assertIn('|', table)
        self.assertIn('+', table)
        self.assertNotIn('│', table)

    def test_to_str_table_respects_locale(self):
        """ The 'table' output format of to_str respects the locale. """
        with mock.patch.dict(os.environ, {'LC_ALL': 'C'}):
            table = twodim.to_str('table', self.HEAD, self.ROWS)
        self.assertIn('+', table)
        self.assertNotIn('│', table)


if __name__ == '__main__':
    unittest.main()
