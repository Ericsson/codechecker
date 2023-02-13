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
from argparse import Namespace

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.analyzers.clangtidy.analyzer import ClangTidy
from codechecker_analyzer.analyzers.config_handler import CheckerState
from codechecker_analyzer.analyzers.clangtidy.config_handler \
        import is_compiler_warning

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.buildlog import log_parser


class MockCheckerLabels:
    def checkers_by_labels(self, labels):
        if labels[0] == 'profile:default':
            return ['core', 'deadcode', 'security.FloatLoopCounter']
        elif labels[0] == 'profile:security':
            return ['alpha.security']
        elif labels[0] == 'guideline:sei-cert':
            return ['alpha.core.CastSize', 'alpha.core.CastToStruct']
        elif labels[0] == 'severity:LOW':
            return ['security.insecureAPI.bcmp', 'alpha.llvm.Conventions']

    def get_description(self, label):
        if label == 'profile':
            return ['default', 'sensitive', 'security', 'portability',
                    'extreme']

    def occurring_values(self, label):
        if label == 'guideline':
            return ['sei-cert']
        elif label == 'sei-cert':
            return ['rule1', 'rule2']


def create_analyzer_sa():
    args = []
    cfg_handler = ClangSA.construct_config_handler(args)

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
        context = analyzer_context.get_context()
        context._checker_labels = MockCheckerLabels()

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

        # Checkers covering some LOW severity rules.
        low_severity = [
                'security.insecureAPI.bcmp',
                'alpha.llvm.Conventions']

        checkers = []
        checkers.extend(map(add_description, security_profile_alpha))
        checkers.extend(map(add_description, default_profile))
        checkers.extend(map(add_description, cert_guideline))

        # "default" profile checkers are enabled explicitly. Others are in
        # "default" state.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers)
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))
        self.assertTrue(all_with_status(CheckerState.default)
                        (cfg_handler.checks(), security_profile_alpha))

        # "--enable-all" leaves alpha checkers in "default" state. Others
        # become enabled.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers, enable_all=True)
        self.assertTrue(all_with_status(CheckerState.default)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable alpha checkers explicitly.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers, [('alpha', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable "security" profile checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('profile:security', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable "security" profile checkers without "profile:" prefix.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('security', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))

        # Enable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('guideline:sei-cert', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), cert_guideline))

        # Enable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('sei-cert', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), cert_guideline))

        # Disable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('guideline:sei-cert', False)])
        self.assertTrue(all_with_status(CheckerState.disabled)
                        (cfg_handler.checks(), cert_guideline))

        # Disable "sei-cert" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('sei-cert', False)])
        self.assertTrue(all_with_status(CheckerState.disabled)
                        (cfg_handler.checks(), cert_guideline))

        # Enable "LOW" severity checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('severity:LOW', True)])
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), low_severity))


def create_analyzer_tidy(args=[]):
    cfg_handler = ClangTidy.construct_config_handler(args)

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

    def test_disable_clangsa_checkers(self):
        """
        Test that checker config still disables clang-analyzer-*.
        """
        analyzer = create_analyzer_tidy()
        result_handler = create_result_handler(analyzer)

        for arg in analyzer.construct_analyzer_cmd(result_handler):
            if arg.startswith('-checks='):
                self.assertIn('-clang-analyzer-*', arg)

        analyzer.config_handler.checker_config = \
            '{"Checks": "hicpp-use-nullptr"}'

        for arg in analyzer.construct_analyzer_cmd(result_handler):
            if arg.startswith('-checks='):
                self.assertIn('-clang-analyzer-*', arg)

        self.assertTrue(is_compiler_warning('Wreserved-id-macro'))
        self.assertFalse(is_compiler_warning('hicpp'))

        args = Namespace()
        args.ordered_checkers = [('Wreserved-id-macro', True)]
        analyzer = create_analyzer_tidy(args)
        result_handler = create_result_handler(analyzer)

        analyzer.config_handler.checker_config = '{}'
        analyzer.config_handler.analyzer_config = \
            {'take-config-from-directory': 'true'}

        for arg in analyzer.construct_analyzer_cmd(result_handler):
            self.assertFalse(arg.startswith('-checks'))

        self.assertEqual(
                analyzer.config_handler.checks()['Wreserved-id-macro'][0],
                CheckerState.enabled)

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
