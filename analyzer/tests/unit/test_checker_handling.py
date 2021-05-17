# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Test the handling of implicitly and explicitly handled checkers in analyzers
"""


import unittest

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.analyzers.clangtidy.analyzer import ClangTidy
from codechecker_analyzer.analyzers.config_handler import CheckerState

from codechecker_analyzer.buildlog import log_parser


class MockContextSA:
    class ProfileMap:
        def __getitem__(self, key):
            return 'profile1'

        def by_profile(self, profile):
            if profile == 'default':
                return ['core', 'deadcode', 'security.FloatLoopCounter']
            elif profile == 'security':
                return ['alpha.security']

        def available_profiles(self):
            return {'default': 'description', 'security': 'description'}

    class GuidelineMap:
        def __getitem__(self, key):
            return {'sei-cert': ['rule1', 'rule2']}

        def by_guideline(self, guideline):
            return ['alpha.core.CastSize', 'alpha.core.CastToStruct']

        def available_guidelines(self):
            return {'sei-cert': 'description'}

    path_env_extra = None
    ld_lib_path_extra = None
    checker_plugin = None
    analyzer_binaries = {'clangsa': 'clang'}
    profile_map = ProfileMap()
    guideline_map = GuidelineMap()
    available_profiles = ['profile1']
    package_root = './'


def create_analyzer_sa():
    args = []
    context = MockContextSA()
    cfg_handler = ClangSA.construct_config_handler(args, context)

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
        'directory': '/'}
    build_action = log_parser.parse_options(action)

    return ClangSA(cfg_handler, build_action)


def create_result_handler(analyzer):
    """
    Create result handler for construct_analyzer_cmd call.
    """

    build_action = analyzer.buildaction

    rh = analyzer.construct_result_handler(
        build_action,
        build_action.directory,
        None,
        None)

    rh.analyzed_source_file = build_action.source

    return rh


class CheckerHandlingClangSATest(unittest.TestCase):
    """
    Test that Clang Static Analyzer manages its default checkers, but
    explicitly enabling or disabling a checker results in compiler flags being
    used.
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

    def test_checker_initializer(self):
        """
        Test initialize_checkers() function.
        """
        def add_description(checker):
            return checker, ''

        def all_with_status(status):
            def f(checks, checkers):
                result = set(check for check, data in checks.items()
                             if data[0] == status)
                return set(checkers) <= result
            return f

        args = []
        context = MockContextSA()

        # "security" profile, but alpha -> not in default.
        security_profile_alpha = [
                'alpha.security.ArrayBound',
                'alpha.security.MallocOverflow']

        # "default" profile.
        default_profile = [
                'security.FloatLoopCounter',
                'deadcode.DeadStores']

        # Checkers covering some "sei-cert" rules.
        cert_guideline = [
                'alpha.core.CastSize',
                'alpha.core.CastToStruct']

        checkers = []
        checkers.extend(map(add_description, security_profile_alpha))
        checkers.extend(map(add_description, default_profile))
        checkers.extend(map(add_description, cert_guideline))

        # "default" profile checkers are enabled explicitly. Others are in
        # "default" state.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers)
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))
        self.assertTrue(all_with_status(CheckerState.default)
                        (cfg_handler.checks(), security_profile_alpha))

        # "--enable-all" leaves alpha checkers in "default" state. Others
        # become enabled.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers, enable_all=True)
        self.assertTrue(all_with_status(CheckerState.default)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable alpha checkers explicitly.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers, [('alpha', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable "security" profile checkers.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers,
                                        [('profile:security', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable "security" profile checkers without "profile:" prefix.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers,
                                        [('security', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers,
                                        [('guideline:sei-cert', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), cert_guideline))

        # Enable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers,
                                        [('sei-cert', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), cert_guideline))

        # Disable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers,
                                        [('guideline:sei-cert', False)])
        self.assertTrue(all_with_status(CheckerState.disabled)
                        (cfg_handler.checks(), cert_guideline))

        # Disable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args, context)
        cfg_handler.initialize_checkers(context, checkers,
                                        [('sei-cert', False)])
        self.assertTrue(all_with_status(CheckerState.disabled)
                        (cfg_handler.checks(), cert_guideline))


class MockContextTidy:
    class ProfileMap:
        def __getitem__(self, key):
            return 'profile1'

        def by_profile(self, profile):
            return 'd-e'

    path_env_extra = None
    ld_lib_path_extra = None
    checker_plugin = None
    analyzer_binaries = {'clang-tidy': 'clang-tidy'}
    profile_map = ProfileMap()
    guideline_map = {'d-e': {'guideline1': ['rule1', 'rule2']}}
    available_profiles = ['profile1']
    package_root = './'


def create_analyzer_tidy():
    args = []
    context = MockContextTidy()
    cfg_handler = ClangTidy.construct_config_handler(args, context)

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
        'directory': '/'}
    build_action = log_parser.parse_options(action)

    return ClangTidy(cfg_handler, build_action)


class CheckerHandlingClangTidyTest(unittest.TestCase):
    """
    Test that Clang Tidy manages its default checkers, but explicitly
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
        Test that the default checks are not disabled in Clang Tidy.
        """

        self.assertFalse('-*' in self.__class__.checks_list)

    def test_only_clangsa_analyzer_checks_are_disabled(self):
        """
        Test that exactly the clang-analyzer group is disabled in Clang Tidy.
        """

        self.assertTrue('-clang-analyzer-*' in self.__class__.checks_list)
        self.assertFalse(
            any(check.startswith('-') and check != '-clang-analyzer-*'
                for check in self.__class__.checks_list))
