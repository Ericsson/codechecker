# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test cases to trim a path by using prefixes. """


import unittest

from codechecker_common.util import trim_path_prefixes


class TrimPathPrefixTestCase(unittest.TestCase):
    """
    Test cases to trim a path by using prefixes.
    """

    def test_no_prefix(self):
        test_path = '/a/b/c'
        self.assertEqual(test_path, trim_path_prefixes(test_path, None))
        self.assertEqual(test_path, trim_path_prefixes(test_path, []))
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['x']))

    def test_only_root_matches(self):
        test_path = '/a/b/c'
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/']))
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/x']))

    def test_one_matches(self):
        test_path = '/a/b/c'
        self.assertEqual('b/c', trim_path_prefixes(test_path, ['/a']))
        self.assertEqual('c', trim_path_prefixes(test_path, ['/a/b']))

    def test_longest_matches(self):
        test_path = '/a/b/c'
        self.assertEqual('b/c', trim_path_prefixes(test_path, ['/a']))
        self.assertEqual('c', trim_path_prefixes(test_path, ['/a', '/a/b']))

    def test_file_path(self):
        test_path = '/a/b/c/foo.txt'
        self.assertEqual('foo.txt', trim_path_prefixes(test_path, ['/a/b/c']))

    def test_prefix_in_dir_name(self):
        test_path = '/a/b/common/foo.txt'
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/a/b/c']))
        self.assertEqual('foo.txt',
                         trim_path_prefixes(test_path, ['/a/b/common']))

    def test_prefix_in_filename(self):
        test_path = '/a/b/common.txt'
        self.assertEqual(test_path, trim_path_prefixes(test_path, ['/a/b/c']))
        self.assertEqual(test_path,
                         trim_path_prefixes(test_path, ['/a/b/common']))
        self.assertEqual('common.txt',
                         trim_path_prefixes(test_path, ['/a/b/']))
