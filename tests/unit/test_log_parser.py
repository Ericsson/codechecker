# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

""" Test the log parser which builds build actions from JSON CCDBs. """

import os
import unittest

from libcodechecker.analyze import log_parser
from libcodechecker.log import option_parser
from libcodechecker.libhandlers.analyze import ParseLogOptions


class LogParserTest(unittest.TestCase):
    """
    Test the log parser which convers logfiles (JSON CCDBs) to build action
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

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]
        results = option_parser.parse_options(build_action.original_command)

        self.assertEqual(' '.join(results.files),
                         r'"-DVARIABLE="some value"" /tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 0)

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

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]

        self.assertEqual(list(build_action.sources)[0], r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="\"some value"\"')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "ldlogger-new-space.json")

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]

        self.assertEqual(list(build_action.sources)[0], r'/tmp/a b.cpp')
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

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]

        self.assertEqual(list(build_action.sources)[0], r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="\"some value"\"')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "intercept-old-space.json")

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]

        self.assertEqual(list(build_action.sources)[0], r'/tmp/a b.cpp')
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

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]

        self.assertEqual(list(build_action.sources)[0], r'/tmp/a.cpp')
        self.assertEqual(len(build_action.analyzer_options), 1)
        self.assertTrue(len(build_action.target) > 0)
        self.assertEqual(build_action.analyzer_options[0],
                         r'-DVARIABLE="\"some value"\"')

        # Test source file with spaces.
        logfile = os.path.join(self.__test_files, "intercept-new-space.json")

        build_action = log_parser.parse_log(logfile, ParseLogOptions())[0]

        self.assertEqual(list(build_action.sources)[0], r'/tmp/a b.cpp')
        self.assertEqual(build_action.lang, 'c++')
