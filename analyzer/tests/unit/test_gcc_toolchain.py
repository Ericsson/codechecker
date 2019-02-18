# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Clang gcc-toolchain compiler option related tests.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import shlex
import unittest

from codechecker.analyze import gcc_toolchain


class GCCToolchainTest(unittest.TestCase):
    """
    gcc toolchain detection tests.
    """

    def test_tc_detect(self):
        """
        Parse gcc-toolchain argument from clang compile command.
        """

        compilation_action = "clang -x c -O3 " \
            "--gcc-toolchain=/home/user/my_gcc/toolchain -c main.cpp "

        toolchain = \
            gcc_toolchain.toolchain_in_args(shlex.split(compilation_action))
        print(toolchain)
        self.assertEqual(toolchain, "/home/user/my_gcc/toolchain")

    def test_get_tc_gcc_compiler(self):
        """
        Get gcc compiler from the toolchain path.
        """
        compilation_action = \
            "clang --gcc-toolchain=/home/user/my_gcc/toolchain"

        toolchain = \
            gcc_toolchain.toolchain_in_args(shlex.split(compilation_action))
        print(toolchain)
        self.assertEqual(toolchain, "/home/user/my_gcc/toolchain")

        tc_compiler_c = gcc_toolchain.get_toolchain_compiler(toolchain, "c")

        print(tc_compiler_c)
        self.assertEqual(tc_compiler_c,
                         "/home/user/my_gcc/toolchain/bin/gcc")

    def test_get_tc_cpp_compiler(self):
        """
        Get g++ compiler from the toolchain path.
        """
        compilation_action = \
            "clang --gcc-toolchain=/home/user/my_gcc/toolchain"

        toolchain = \
            gcc_toolchain.toolchain_in_args(shlex.split(compilation_action))
        print(toolchain)
        self.assertEqual(toolchain, "/home/user/my_gcc/toolchain")

        tc_compiler_cpp = gcc_toolchain.get_toolchain_compiler(toolchain,
                                                               "c++")

        print(tc_compiler_cpp)
        self.assertEqual(tc_compiler_cpp,
                         "/home/user/my_gcc/toolchain/bin/g++")
