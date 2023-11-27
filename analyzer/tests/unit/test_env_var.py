# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Tests for environmental variables recognized by CodeChecker.
"""


import unittest

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.analyzers.gcc.analyzer import Gcc
from codechecker_analyzer.buildlog import log_parser


def create_analyzer_gcc():
    args = []
    cfg_handler = Gcc.construct_config_handler(args)

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
        'directory': '/'}
    build_action = log_parser.parse_options(action)

    return Gcc(cfg_handler, build_action)


class EnvVarTest(unittest.TestCase):

    def setup_class(self):
        context = analyzer_context.get_context()
        self.__original_analyzer_env = context.analyzer_env

    def teardown_method(self, method):
        # Reset the environment, and some some initializer methods to hopefully
        # reset the state of the analyzer context.
        context = analyzer_context.get_context()
        context.__analyzer_env = self.__original_analyzer_env
        context._Context__populate_analyzers()

    def _get_analyzer_bin_for_CC_ANALYZER_BIN(self, analyzer_bin_conf: str):
        """
        Set the CC_ANALYZER_BIN env variable, which is an
          "analyzer plugin" -> "path to binary"
        mapping, and return the binary path the GCC analyzer in CodeChecker was
        initialized with (the intend being that GCC should've been
        initialized with the binary that was given by the env var).
        """
        context = analyzer_context.get_context()
        context.analyzer_env["CC_ANALYZER_BIN"] = analyzer_bin_conf
        context._Context__populate_analyzers()

        analyzer = create_analyzer_gcc()
        return analyzer.analyzer_binary()

    def test_CC_ANALYZER_BIN(self):
        """
        Test whether GCC runs the appropriate binary when CC_ANALYZER_BIN is
        set.
        For GCC, it doesn't matter whether we use the 'gcc' or the 'g++'
        binary; we exploit this fact by setting the variable to these values
        respectively, and check whether the GCC analyzer points to them. Every
        machine is expected to run some version of gcc, so this should be OK.
        """
        bin_gcc_var = self._get_analyzer_bin_for_CC_ANALYZER_BIN("gcc:gcc")
        self.assertIn("gcc", bin_gcc_var)
        self.assertNotIn("g++", bin_gcc_var)

        bin_gpp_var = self._get_analyzer_bin_for_CC_ANALYZER_BIN("gcc:g++")
        self.assertIn("g++", bin_gpp_var)
        self.assertNotIn("gcc", bin_gpp_var)

        self.assertNotEqual(bin_gcc_var, bin_gpp_var)

    def test_CC_ANALYZER_BIN_overrides_CC_ANALYZERS_FROM_PATH(self):
        """
        Check whether CC_ANALYZER_BIN overrides CC_ANALYZERS_FROM_PATH (which
        is what we want).
        """

        context = analyzer_context.get_context()
        context.analyzer_env["CC_ANALYZERS_FROM_PATH"] = '1'

        bin_gcc_var = self._get_analyzer_bin_for_CC_ANALYZER_BIN("gcc:gcc")
        self.assertIn("gcc", bin_gcc_var)
        self.assertNotIn("g++", bin_gcc_var)

        bin_gpp_var = self._get_analyzer_bin_for_CC_ANALYZER_BIN("gcc:g++")
        self.assertIn("g++", bin_gpp_var)
        self.assertNotIn("gcc", bin_gpp_var)

        self.assertNotEqual(bin_gcc_var, bin_gpp_var)
