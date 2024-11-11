# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""Compiler flag checking functions."""


import unittest

from codechecker_analyzer.analyzers.clangsa import ctu_triple_arch


class TripleArch(unittest.TestCase):
    """Compiler flag related tests."""

    def test_triple_arch(self):
        output = '''
clang version 8.0.0 (tags/RELEASE_800/final)
Target: x86_64-unknown-linux-gnu
Thread model: posix
InstalledDir: /opt/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04/bin
 "/opt/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04/bin/clang-8" "-cc1"
 "-triple" "x86_64-unknown-linux-gnu" "<blabla>" "main.cpp"
 "<blabla>"
 '''
        self.assertEqual(
            ctu_triple_arch._find_arch_in_command(output),
            'x86_64')

        output = '''
clang version 8.0.0 (tags/RELEASE_800/final)
Target: x86_64-unknown-linux-gnu
Thread model: posix
InstalledDir: /opt/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04/bin
 "/opt/clang+llvm-8.0.0-x86_64-linux-gnu-ubuntu-18.04/bin/clang-8" "-cc1"
 "<blabla>" "main.cpp" "<blabla>"
 '''
        self.assertIsNone(ctu_triple_arch._find_arch_in_command(output))
