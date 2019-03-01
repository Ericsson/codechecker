# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Test the log parser which builds build actions from JSON CCDBs. """
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

from codechecker_analyzer.buildlog import log_parser
from codechecker_common.util import load_json_or_empty


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

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

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

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE=some value')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "ldlogger-new-space.json")

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

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

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="some')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "intercept-old-space.json")

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

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

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

        self.assertEqual(build_action.source, r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="some value"')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "intercept-new-space.json")

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

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

        build_actions = log_parser.parse_log(preprocessor_actions)
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

        build_actions = log_parser.parse_log(preprocessor_actions)
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

        build_actions = log_parser.parse_log(preprocessor_actions)
        self.assertEqual(len(build_actions), 0)

    def test_include_rel_to_abs(self):
        """
        Test working directory prepending to relative include paths.
        """
        logfile = os.path.join(self.__test_files, "include.json")

        build_action = log_parser.parse_log(load_json_or_empty(logfile))[0]

        self.assertEqual(len(build_action.analyzer_options), 4)
        self.assertEqual(build_action.analyzer_options[0], '-I')
        self.assertEqual(build_action.analyzer_options[1], '/include')
        self.assertEqual(build_action.analyzer_options[2], '-I/include')
        self.assertEqual(build_action.analyzer_options[3], '-I/tmp')
