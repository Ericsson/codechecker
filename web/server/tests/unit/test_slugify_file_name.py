# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test slugify file names. """


import unittest

from codechecker_server.api.report_server import slugify


class SlugifyFileNameTestCase(unittest.TestCase):
    """
    Test cases to slugify file names.
    """

    def test_only_alpha(self):
        self.assertEqual('test', slugify('test'))
        self.assertEqual('test123', slugify('test123'))

    def test_white_spaces(self):
        self.assertEqual('test_1', slugify('test 1'))
        self.assertEqual('test_1_2', slugify('test 1 2'))

    def test_underscore(self):
        self.assertEqual('test_1', slugify('test_1'))
        self.assertEqual('test_1_2', slugify('test_1_2'))

    def test_slashes(self):
        self.assertEqual('test_1', slugify('test/1'))
        self.assertEqual('test_1_2', slugify('test/1/2'))

    def test_special_characters(self):
        self.assertEqual('test', slugify('test*?#'))
