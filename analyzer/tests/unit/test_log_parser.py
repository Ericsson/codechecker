# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test the log parser which builds build actions from JSON CCDBs. """


import json
import os
import shutil
import tempfile
import unittest

from codechecker_analyzer.buildlog import log_parser
from codechecker_common.util import load_json_or_empty
from codechecker_common import skiplist_handler


class LogParserTest(unittest.TestCase):
    """
    Test the log parser which converts logfiles (JSON CCDBs) to build action
    lists.
    """

    @classmethod
    def setup_class(cls):
        """Initialize test resources."""

        # Already generated JSONs for the tests.
        cls.__this_dir = os.path.dirname(__file__)
        cls.__test_files = os.path.join(cls.__this_dir,
                                        'logparser_test_files')

        cls.tmp_dir = tempfile.mkdtemp()
        cls.src_file_path = os.path.join(cls.tmp_dir, "main.cpp")
        cls.rsp_file_path = os.path.join(cls.tmp_dir, "main.rsp")
        cls.compile_command_file_path = os.path.join(cls.tmp_dir,
                                                     "compile_command.json")
        with open(cls.src_file_path, "w",
                  encoding="utf-8", errors="ignore") as src_file:
            src_file.write("int main() { return 0; }")

    @classmethod
    def teardown_class(cls):
        """
        Clean temporary directory and remove compiler_info.json file.
        """
        compiler_info = os.path.join(cls.__this_dir, 'compiler_info.json')
        if os.path.exists(compiler_info):
            os.remove(compiler_info)

        shutil.rmtree(cls.tmp_dir)

    def test_old_ldlogger(self):
        """
        Test log file parsing escape behaviour with pre-2017 Q2 LD-LOGGER.
        """
        logfile = os.path.join(self.__test_files, "ldlogger-old.json")

        # LD-LOGGER before http://github.com/Ericsson/codechecker/pull/631
        # used an escape mechanism that, when parsed by the log parser via
        # shlex, made CodeChecker parse arguments with multiword string
        # literals in them be considered as "file" (instead of compile option),
        # eventually ignored by the command builder, thus lessening analysis
        # accuracy, as defines were lost.
        #
        # Logfile contains "-DVARIABLE="some value"".
        #
        # There is no good way to back-and-forth convert in log_parser or
        # option_parser, so here we aim for a non-failing stalemate of the
        # define being considered a file and ignored, for now.

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)

    def test_new_ldlogger(self):
        """
        Test log file parsing escape behaviour with after-#631 LD-LOGGER.
        """
        logfile = os.path.join(self.__test_files, "ldlogger-new.json")

        # LD-LOGGERS after http://github.com/Ericsson/codechecker/pull/631
        # now properly log the multiword arguments. When these are parsed by
        # the log_parser, the define's value will be passed to the analyzer.
        #
        # Logfile contains -DVARIABLE="some value"
        # and --target=x86_64-linux-gnu.

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE=some value')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "ldlogger-new-space.json")

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, r'/tmp/a b.cpp')
        self.assertEqual(build_action.lang, 'c++')

    def test_old_intercept_build(self):
        """
        Test log file parsing escape behaviour with clang-5.0 intercept-build.
        """
        logfile = os.path.join(self.__test_files, "intercept-old.json")

        # Scan-build-py shipping with clang-5.0 makes a logfile that contains:
        # -DVARIABLE=\"some value\" and --target=x86_64-linux-gnu
        #
        # The define is passed to the analyzer properly.

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="some')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "intercept-old-space.json")

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, '/tmp/a b.cpp')
        self.assertEqual(build_action.lang, 'c++')

    def test_new_intercept_build(self):
        """
        Test log file parsing escapes with upstream (GitHub) intercept-build.
        """
        logfile = os.path.join(self.__test_files, "intercept-new.json")

        # Upstream scan-build-py creates an argument vector, as opposed to a
        # command string. This argument vector contains the define as it's
        # element in the following format:
        # -DVARIABLE=\"some value\"
        # and the target triplet, e.g.:
        # --target=x86_64-linux-gnu
        #
        # The define is passed to the analyzer properly.

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="some value"')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "intercept-new-space.json")

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(build_action.source, '/tmp/a b.cpp')
        self.assertEqual(build_action.lang, 'c++')

    def test_omit_preproc(self):
        """
        Compiler preprocessor actions should be omitted.
        """
        preprocessor_actions = [
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -c /tmp/a.cpp",
             "file": "/tmp/a.cpp"},
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -E /tmp/a.cpp",
             "file": "/tmp/a.cpp"},
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -MT /tmp/a.cpp",
             "file": "/tmp/a.cpp"},
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -MM /tmp/a.cpp",
             "file": "/tmp/a.cpp"},
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -MF /tmp/a.cpp",
             "file": "/tmp/a.cpp"},
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -M /tmp/a.cpp",
             "file": "/tmp/a.cpp"}]

        build_actions, _ = \
            log_parser.parse_unique_log(preprocessor_actions,
                                        self.__this_dir)
        self.assertEqual(len(build_actions), 1)
        self.assertTrue('-M' not in build_actions[0].original_command)
        self.assertTrue('-E' not in build_actions[0].original_command)
        self.assertTrue('-c' in build_actions[0].original_command)

    def test_keep_compile_and_dep(self):
        """ Keep the compile command if -MD is set.
        Dependency generation is done as a side effect of the compilation.
        """
        preprocessor_actions = [
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -MD /tmp/a.cpp",
             "file": "/tmp/a.cpp"}]

        build_actions, _ = log_parser.parse_unique_log(preprocessor_actions,
                                                       self.__this_dir)
        self.assertEqual(len(build_actions), 1)
        self.assertTrue('-MD' in build_actions[0].original_command)

    def test_omit_dep_with_e(self):
        """ Skip the compile command if -MD is set together with -E. """

        preprocessor_actions = [
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -MD -E /tmp/a.cpp",
             "file": "/tmp/a.cpp"},
            {"directory": "/tmp",
             "command": "g++ /tmp/a.cpp -E -MD /tmp/a.cpp",
             "file": "/tmp/a.cpp"}]

        build_actions, _ = log_parser.parse_unique_log(preprocessor_actions,
                                                       self.__this_dir)
        self.assertEqual(len(build_actions), 0)

    def test_include_rel_to_abs(self):
        """
        Test working directory prepending to relative include paths.
        """
        logfile = os.path.join(self.__test_files, "include.json")

        build_actions, _ = log_parser.\
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(len(build_action.analyzer_options), 4)
        self.assertEqual(build_action.analyzer_options[0], '-I')
        self.assertEqual(build_action.analyzer_options[1], '/include')
        self.assertEqual(build_action.analyzer_options[2], '-I/include')
        self.assertEqual(build_action.analyzer_options[3], '-I/tmp')

    def test_compiler_extra_args_filter_empty(self):
        """Filtering no flags."""

        flags = []
        filtered = log_parser.filter_compiler_includes_extra_args(flags)
        self.assertEqual(filtered, [])

    def test_compiler_implicit_include_flags(self):
        """Specific stdlib, build architecture related flags should be kept."""

        flags = ["-I", "/usr/include", "-m64", "-stdlib=libc++", "-std=c++17"]
        filtered = log_parser.filter_compiler_includes_extra_args(flags)
        self.assertEqual(filtered, ["-m64", "-stdlib=libc++", "-std=c++17"])

    def test_compiler_implicit_include_flags_sysroot(self):
        """sysroot flags should be kept."""

        flags = ["-I", "/usr/include", "--sysroot=/usr/mysysroot"]
        filtered = log_parser.filter_compiler_includes_extra_args(flags)
        self.assertEqual(filtered, ["--sysroot=/usr/mysysroot"])

    def test_skip_everything_from_parse(self):
        """Same skip file for pre analysis and analysis. Skip everything."""
        cmp_cmd_json = [
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/a.cpp",
             "file": "a.cpp"},
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/b.cpp",
             "file": "b.cpp"},
            {"directory": "/tmp/lib2",
             "command": "g++ /tmp/lib2/a.cpp",
             "file": "a.cpp"}]

        skip_list = """
        -*/lib1/*
        -*/lib2/*
        """
        analysis_skip = skiplist_handler.SkipListHandler(skip_list)
        pre_analysis_skip = skiplist_handler.SkipListHandler(skip_list)

        build_actions, _ = log_parser.\
            parse_unique_log(cmp_cmd_json, self.__this_dir,
                             analysis_skip_handler=analysis_skip,
                             pre_analysis_skip_handler=pre_analysis_skip)

        self.assertEqual(len(build_actions), 0)

    def test_skip_everything_from_parse_relative_path(self):
        """
        Same skip file for pre analysis and analysis. Skip everything.
        Source file contains relative path.
        """
        cmp_cmd_json = [
            {"directory": "/tmp/lib1/Debug",
             "command": "g++ ../a.cpp",
             "file": "../a.cpp"},
            {"directory": "/tmp/lib1/Debug/rel",
             "command": "g++ ../../b.cpp",
             "file": "../../b.cpp"},
            {"directory": "/tmp/lib1/Debug",
             "command": "g++ ../d.cpp",
             "file": "../d.cpp"},
            {"directory": "/tmp/lib2/Debug",
             "command": "g++ ../a.cpp",
             "file": "../a.cpp"}]

        skip_list = """
        +/tmp/lib1/d.cpp
        -*/lib1/Debug/rel/../../*
        -*/lib1/a.cpp
        -/tmp/lib2/a.cpp
        """
        analysis_skip = skiplist_handler.SkipListHandler(skip_list)
        pre_analysis_skip = skiplist_handler.SkipListHandler(skip_list)

        build_actions, _ = log_parser.\
            parse_unique_log(cmp_cmd_json, self.__this_dir,
                             analysis_skip_handler=analysis_skip,
                             pre_analysis_skip_handler=pre_analysis_skip)

        self.assertEqual(len(build_actions), 1)
        self.assertEqual(build_actions[0].source, '/tmp/lib1/d.cpp')

    def test_skip_all_in_pre_from_parse(self):
        """Pre analysis skips everything but keep build action for analysis."""
        cmp_cmd_json = [
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/a.cpp",
             "file": "a.cpp"},
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/b.cpp",
             "file": "b.cpp"},
            {"directory": "/tmp/lib2",
             "command": "g++ /tmp/lib2/a.cpp",
             "file": "a.cpp"}]

        keep = cmp_cmd_json[2]

        skip_list = """
        -*/lib1/*
        """
        pre_skip_list = """
        -*
        """
        analysis_skip = skiplist_handler.SkipListHandler(skip_list)
        pre_analysis_skip = skiplist_handler.SkipListHandler(pre_skip_list)

        build_actions, _ = log_parser.\
            parse_unique_log(cmp_cmd_json, self.__this_dir,
                             analysis_skip_handler=analysis_skip,
                             pre_analysis_skip_handler=pre_analysis_skip)

        self.assertEqual(len(build_actions), 1)

        source_file = os.path.join(keep['directory'], keep['file'])
        self.assertEqual(build_actions[0].source, source_file)
        self.assertEqual(build_actions[0].original_command, keep['command'])

    def test_skip_no_pre_from_parse(self):
        """Keep everything pre analysis needs it in ctu or statistics mode."""
        cmp_cmd_json = [
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/a.cpp",
             "file": "a.cpp"},
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/b.cpp",
             "file": "b.cpp"},
            {"directory": "/tmp/lib2",
             "command": "g++ /tmp/lib2/a.cpp",
             "file": "a.cpp"}]

        skip_list = """
        -*/lib1/*
        """
        analysis_skip = skiplist_handler.SkipListHandler(skip_list)
        pre_analysis_skip = skiplist_handler.SkipListHandler("")

        build_actions, _ = log_parser.\
            parse_unique_log(cmp_cmd_json, self.__this_dir,
                             analysis_skip_handler=analysis_skip,
                             ctu_or_stats_enabled=True,
                             pre_analysis_skip_handler=pre_analysis_skip)

        self.assertEqual(len(build_actions), 3)

    def test_no_skip_from_parse(self):
        """Keep everything for analysis, no skipping there."""
        cmp_cmd_json = [
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/a.cpp",
             "file": "a.cpp"},
            {"directory": "/tmp/lib1",
             "command": "g++ /tmp/lib1/b.cpp",
             "file": "b.cpp"},
            {"directory": "/tmp/lib2",
             "command": "g++ /tmp/lib2/a.cpp",
             "file": "a.cpp"}]

        skip_list = """
        -*/lib1/*
        """
        analysis_skip = skiplist_handler.SkipListHandler("")
        pre_analysis_skip = skiplist_handler.SkipListHandler(skip_list)

        build_actions, _ = log_parser.\
            parse_unique_log(cmp_cmd_json, self.__this_dir,
                             analysis_skip_handler=analysis_skip,
                             pre_analysis_skip_handler=pre_analysis_skip)

        self.assertEqual(len(build_actions), 3)

    def test_response_file_simple(self):
        """
        Test simple response file where the source file comes outside the
        response file.
        """
        with open(self.compile_command_file_path, "w",
                  encoding="utf-8", errors="ignore") as build_json:
            build_json.write(json.dumps([dict(
                directory=self.tmp_dir,
                command="g++ {0} @{1}".format(self.src_file_path,
                                              self.rsp_file_path),
                file=self.src_file_path
            )]))

        with open(self.rsp_file_path, "w",
                  encoding="utf-8", errors="ignore") as rsp_file:
            rsp_file.write("""-DVARIABLE="some value" """)

        logfile = os.path.join(self.compile_command_file_path)

        build_actions, _ = log_parser. \
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertEqual(build_action.analyzer_options[0], '-DVARIABLE=some')

    def test_response_file_contains_source_file(self):
        """
        Test response file where the source file comes from the response file.
        """
        with open(self.compile_command_file_path, "w",
                  encoding="utf-8", errors="ignore") as build_json:
            build_json.write(json.dumps([dict(
                directory=self.tmp_dir,
                command="g++ @{0}".format(self.rsp_file_path),
                file="@{0}".format(self.rsp_file_path)
            )]))

        with open(self.rsp_file_path, "w",
                  encoding="utf-8", errors="ignore") as rsp_file:
            rsp_file.write("""-DVARIABLE="some value" {0}""".format(
                self.src_file_path))

        logfile = os.path.join(self.compile_command_file_path)

        build_actions, _ = log_parser. \
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)
        build_action = build_actions[0]

        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertEqual(build_action.source, self.src_file_path)
        self.assertEqual(build_action.analyzer_options[0], '-DVARIABLE=some')

    def test_response_file_contains_multiple_source_files(self):
        """
        Test response file where multiple source files come from the response
        file.
        """
        with open(self.compile_command_file_path, "w",
                  encoding="utf-8", errors="ignore") as build_json:
            build_json.write(json.dumps([dict(
                directory=self.tmp_dir,
                command="g++ @{0}".format(self.rsp_file_path),
                file="@{0}".format(self.rsp_file_path)
            )]))

        a_file_path = os.path.join(self.tmp_dir, "a.cpp")
        with open(a_file_path, "w",
                  encoding="utf-8", errors="ignore") as src_file:
            src_file.write("int main() { return 0; }")

        b_file_path = os.path.join(self.tmp_dir, "b.cpp")
        with open(b_file_path, "w",
                  encoding="utf-8", errors="ignore") as src_file:
            src_file.write("void foo() {}")

        with open(self.rsp_file_path, "w",
                  encoding="utf-8", errors="ignore") as rsp_file:
            rsp_file.write("""-DVARIABLE="some value" {0} {1}""".format(
                a_file_path, b_file_path))

        logfile = os.path.join(self.compile_command_file_path)

        build_actions, _ = log_parser. \
            parse_unique_log(load_json_or_empty(logfile), self.__this_dir)

        self.assertEqual(len(build_actions), 2)

        a_build_action = [b for b in build_actions
                          if b.source == a_file_path][0]
        self.assertEqual(len(a_build_action.analyzer_options), 1)
        self.assertEqual(a_build_action.analyzer_options[0], '-DVARIABLE=some')

        b_build_action = [b for b in build_actions
                          if b.source == b_file_path][0]
        self.assertEqual(len(b_build_action.analyzer_options), 1)
        self.assertEqual(b_build_action.analyzer_options[0], '-DVARIABLE=some')
