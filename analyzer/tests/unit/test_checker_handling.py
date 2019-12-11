# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

"""
Test the handling of implicitly and explicitly handled checkers in analyzers
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.analyzers.clangtidy.analyzer import ClangTidy

from codechecker_analyzer.buildlog import log_parser


class MockContextSA(object):
    path_env_extra = None
    ld_lib_path_extra = None
    checker_plugin = None
    analyzer_binaries = {'clangsa': 'clang'}
    compiler_resource_dir = None
    checker_config = {'clangsa_checkers': ['a.b']}
    available_profiles = ['profile1']
    package_root = './'


def create_analyzer_sa():
    # - Begin create config handler
    # -- Begin create args

    args = []

    # -- End create args
    # -- Begin create context

    context = MockContextSA()

    # -- End create context

    cfg_handler = ClangSA.construct_config_handler(args, context)

    # - End create config handler
    # - Begin create build action

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
        'directory': '/'}
    build_action = log_parser.parse_options(action)

    # - End create build action

    return ClangSA(cfg_handler, build_action)


def create_result_handler(analyzer):
    """
    Create result handler for construct_analyzer_cmd call.
    """

    # - Begin create build action

    build_action = analyzer.buildaction

    # - End create build action
    # - Begin create report output

    report_output = build_action.directory

    # - End create report output
    # - Begin create severity map

    severity_map = None

    # - End create severity map
    # - Begin create skiplist handler

    skiplist_handler = None

    # - End create skiplist handler

    rh = analyzer.construct_result_handler(
        build_action,
        report_output,
        severity_map,
        skiplist_handler)

    rh.analyzed_source_file = build_action.source

    return rh


class CheckerHandlingClangSATest(unittest.TestCase):
    """
    Test that the every analyzer manages its default checkers, but explicitly
    enabling or disabling a checker results in compiler flags being used.
    """

    @classmethod
    def setUpClass(cls):
        analyzer = create_analyzer_sa()
        result_handler = create_result_handler(analyzer)
        cls.cmd = analyzer.construct_analyzer_cmd(result_handler)
        print('Analyzer command: %s' % cls.cmd)

    def test_default_checkers_are_not_disabled(self):
        """
        Test that the default checks are not disabled by a specific flag in
        ClangSA.
        """

        self.assertFalse(
            any('--analyzer-no-default-checks' in arg
                for arg in self.__class__.cmd))

    def test_no_disabled_checks(self):
        """
        Test that ClangSA only uses enable lists.
        """
        self.assertFalse(
            any(arg.startswith('-analyzer-disable-checker')
                for arg in self.__class__.cmd))


class MockContextTidy(object):
    path_env_extra = None
    ld_lib_path_extra = None
    checker_plugin = None
    analyzer_binaries = {'clang-tidy': 'clang-tidy'}
    compiler_resource_dir = None
    checker_config = {'clangtidy_checkers': ['d.e']}
    available_profiles = ['profile1']
    package_root = './'


def create_analyzer_tidy():
    # - Begin create config handler
    # -- Begin create args

    args = []

    # -- End create args
    # -- Begin create context

    context = MockContextTidy()

    # -- End create context

    cfg_handler = ClangTidy.construct_config_handler(args, context)

    # - End create config handler
    # - Begin create build action

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
        'directory': '/'}
    build_action = log_parser.parse_options(action)

    # - End create build action

    return ClangTidy(cfg_handler, build_action)


class CheckerHandlingClangTidyTest(unittest.TestCase):
    """
    Test that the every analyzer manages its default checkers, but explicitly
    enabling or disabling a checker results in compiler flags being used.
    """

    @classmethod
    def setUpClass(cls):
        analyzer = create_analyzer_tidy()
        result_handler = create_result_handler(analyzer)
        cls.cmd = analyzer.construct_analyzer_cmd(result_handler)
        print('Analyzer command: %s' % cls.cmd)

        checks_arg = cls.cmd[1]
        checks = checks_arg[len('-checks='):]
        cls.checks_list = checks.split(',')
        print('Checks list: %s' % cls.checks_list)

    def test_default_checkers_are_not_disabled(self):
        """
        Test that the default checks are not disabled in ClangTidy.
        """

        self.assertFalse('-*' in self.__class__.checks_list)

    def test_only_clangsa_analyzer_checks_are_disabled(self):
        """
        Test that exactly the clang-analyzer group is disabled in clang tidy.
        """

        self.assertTrue('-clang-analyzer-*' in self.__class__.checks_list)
        self.assertFalse(
            any(check.startswith('-') and check != '-clang-analyzer-*'
                for check in self.__class__.checks_list))
