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
import tempfile
import os

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

    def teardown_method(self, _):
        # Reset the environment, and some some initializer methods to hopefully
        # reset the state of the analyzer context.
        context = analyzer_context.get_context()
        context._Context__populate_analyzers()

    def _get_analyzer_bin_for_cc_analyzer_bin(self, analyzer_bin_conf: str):
        """
        Set the CC_ANALYZER_BIN env variable, which is an
          "analyzer plugin" -> "path to binary"
        mapping, and return the binary path the GCC analyzer in CodeChecker was
        initialized with (the intend being that GCC should've been
        initialized with the binary that was given by the env var).
        """
        context = analyzer_context.get_context()
        context.cc_env["CC_ANALYZER_BIN"] = analyzer_bin_conf
        context._Context__populate_analyzers()

        analyzer = create_analyzer_gcc()
        return analyzer.analyzer_binary()

    def test_cc_analyzer_bin(self):
        """
        Test whether GCC runs the appropriate binary when CC_ANALYZER_BIN is
        set.
        For GCC, it doesn't matter whether we use the 'gcc' or the 'g++'
        binary; we exploit this fact by setting the variable to these values
        respectively, and check whether the GCC analyzer points to them. Every
        machine is expected to run some version of gcc, so this should be OK.
        """
        bin_gcc_var = self._get_analyzer_bin_for_cc_analyzer_bin("gcc:gcc")
        self.assertTrue(bin_gcc_var.endswith("gcc"))
        self.assertTrue(not bin_gcc_var.endswith("g++"))

        bin_gpp_var = self._get_analyzer_bin_for_cc_analyzer_bin("gcc:g++")
        self.assertTrue(bin_gpp_var.endswith("g++"))
        self.assertTrue(not bin_gpp_var.endswith("gcc"))

        self.assertNotEqual(bin_gcc_var, bin_gpp_var)

    def test_cc_analyzer_bin_overrides_cc_analyzers_from_path(self):
        """
        Check whether CC_ANALYZER_BIN overrides CC_ANALYZERS_FROM_PATH (which
        is what we want).
        """

        context = analyzer_context.get_context()
        context.cc_env["CC_ANALYZERS_FROM_PATH"] = '1'

        bin_gcc_var = self._get_analyzer_bin_for_cc_analyzer_bin("gcc:gcc")
        self.assertTrue(bin_gcc_var.endswith("gcc"))
        self.assertTrue(not bin_gcc_var.endswith("g++"))

        bin_gpp_var = self._get_analyzer_bin_for_cc_analyzer_bin("gcc:g++")
        self.assertTrue(bin_gpp_var.endswith("g++"))
        self.assertTrue(not bin_gpp_var.endswith("gcc"))

        self.assertNotEqual(bin_gcc_var, bin_gpp_var)

    def test_cc_analyzer_internal_env(self):
        """
        Check whether the ld_library_path is extended with the internal
        lib path if internally packaged analyzer is invoked.
        """

        data_files_dir = tempfile.mkdtemp()

        package_layout_json = """
        {
        "ld_lib_path_extra": [],
        "path_env_extra": [],
        "runtime": {
            "analyzers": {
            "clang-tidy": "clang-tidy",
            "clangsa": "cc-bin/packaged-clang",
            "cppcheck": "cppcheck",
            "gcc": "g++"
            },
            "clang-apply-replacements": "clang-apply-replacements",
            "ld_lib_path_extra": [
            "internal_package_lib"
            ],
            "path_env_extra": [
            ]
        }
        }
        """
        config_dir = os.path.join(data_files_dir, "config")
        os.mkdir(config_dir)
        layout_cfg_file = os.path.join(config_dir, "package_layout.json")
        with open(layout_cfg_file, "w", encoding="utf-8") as text_file:
            text_file.write(package_layout_json)
        cc_bin_dir = os.path.join(data_files_dir, "cc-bin")
        os.mkdir(cc_bin_dir)
        packaged_clang_file = os.path.join(cc_bin_dir, "packaged-clang")
        with open(packaged_clang_file, "w", encoding="utf-8") as text_file:
            text_file.write("")

        context = analyzer_context.get_context()
        context._data_files_dir_path = data_files_dir

        lcfg_dict = context._Context__get_package_layout()
        context._data_files_dir_path = data_files_dir
        context.pckg_layout = lcfg_dict['runtime']
        context._Context__populate_analyzers()

        # clang-19 is part of the codechecker package
        # so the internal package lib should be in the ld_library_path
        clang_env = context.get_analyzer_env("clangsa")
        env_txt = str(clang_env)
        self.assertTrue(env_txt.find("internal_package_lib") != -1)

        # clang-tidy is not part of the codechecker package
        # so internal package lib should not be in the ld_library_path
        clang_env = context.get_analyzer_env("clang-tidy")
        env_txt = str(clang_env)
        self.assertTrue(env_txt.find("internal_package_lib") == -1)

        os.remove(layout_cfg_file)
        os.remove(packaged_clang_file)
        os.rmdir(cc_bin_dir)
        os.rmdir(config_dir)
        os.rmdir(context._data_files_dir_path)
