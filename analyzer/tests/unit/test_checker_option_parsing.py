# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test the parsing of checker options reported by the analyzers
"""

import unittest
from codechecker_analyzer.analyzers.clangtidy.analyzer \
    import parse_checker_config as clangtidy_parse_checker_config


class ClangTidyParseCheckerConfigTest(unittest.TestCase):
    """
    Test that the checker config options for clang-tidy are parsed correctly.
    """

    def test_old_format(self):
        """
        Test parsing of the output of 'clang-tidy -dump-config -checks=*' for
        clang-tidy up to LLVM 14.
        """
        old_format_example = """
---
Checks:          'clang-diagnostic-*,clang-analyzer-*,clang-diagnostic-*,\
clang-analyzer-*,bugprone-*,-bugprone-easily-swappable-parameters,\
concurrency-*,boost-*,concurrency-*,cppcoreguidelines-init-variables,\
cppcoreguidelines-special-member-functions,misc-*,\
-misc-definitions-in-headers,-misc-non-private-member-variables-in-classes,\
performance-*,-misc-const-correctness,*'
WarningsAsErrors: ''
HeaderFilterRegex: ''
AnalyzeTemporaryDtors: false
FormatStyle:     none
CheckOptions:
  - key:             readability-suspicious-call-argument.PrefixSimilarAbove
    value:           '30'
  - key:             cppcoreguidelines-no-malloc.Reallocations
    value:           '::realloc'
  - key:             llvmlibc-restrict-system-libc-headers.Includes
    value:           '-*'
  - key:             cppcoreguidelines-owning-memory.LegacyResourceConsumers
    value:           '::free;::realloc;::freopen;::fclose'
  - key:             modernize-use-auto.MinTypeNameLength
    value:           '5'
  - key:             bugprone-reserved-identifier.Invert
    value:           'false'
"""
        result = clangtidy_parse_checker_config(old_format_example)
        # The result can be an arbitrary iterable of pair-likes. To make
        # assertions about it easer, we first convert it to a list-of-lists.
        result = [[k, v] for (k, v) in result]
        self.assertEqual(len(result), 6)
        self.assertIn(
            ["readability-suspicious-call-argument:PrefixSimilarAbove",
             "'30'"], result)

    def test_new_format(self):
        """
        Test parsing of the output of 'clang-tidy -dump-config -checks=*' for
        clang-tidy starting with LLVM 15.
        """
        new_format_example = """
---
Checks:          'clang-diagnostic-*,clang-analyzer-*,*'
WarningsAsErrors: ''
HeaderFilterRegex: ''
AnalyzeTemporaryDtors: false
FormatStyle:     none
CheckOptions:
  performance-unnecessary-value-param.IncludeStyle: llvm
  readability-suspicious-call-argument.PrefixSimilarAbove: '30'
  cppcoreguidelines-no-malloc.Reallocations: '::realloc'
  llvmlibc-restrict-system-libc-headers.Includes: '-*'
  bugprone-reserved-identifier.Invert: 'false'
  cert-dcl16-c.IgnoreMacros: 'true'
"""
        result = clangtidy_parse_checker_config(new_format_example)
        # The result can be an arbitrary iterable of pair-likes. To make
        # assertions about it easer, we first convert it to a list-of-lists.
        result = [[k, v] for (k, v) in result]
        self.assertEqual(len(result), 6)
        self.assertIn(
            ["readability-suspicious-call-argument:PrefixSimilarAbove", "30"],
            result)
