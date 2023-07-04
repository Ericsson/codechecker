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


from distutils import util
import os
import re
import unittest
from argparse import Namespace

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.analyzers.clangtidy.analyzer import ClangTidy
from codechecker_analyzer.analyzers.config_handler import CheckerState
from codechecker_analyzer.analyzers.clangtidy.config_handler \
        import is_compiler_warning

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.buildlog import log_parser


class MockClangsaCheckerLabels:
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
        context._checker_labels = MockClangsaCheckerLabels()

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
        # TODO: This test is currently removed, because checkers that are not
        # enabled are explicitly disabled. In a next commit ClangSA reports
        # will be hidden instead of disabled. In that commit this test could be
        # re-enabled.
        pass

        # self.assertFalse(
        #     any(arg.startswith('-analyzer-disable-checker')
        #         for arg in self.__class__.cmd))

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

        statisticsbased = [
                'statisticsbased.SpecialReturnValue',
                'statisticsbased.UncheckedReturnValue']

        checkers = []
        checkers.extend(map(add_description, security_profile_alpha))
        checkers.extend(map(add_description, default_profile))
        checkers.extend(map(add_description, cert_guideline))
        checkers.extend(map(add_description, statisticsbased))

        # "default" profile checkers are enabled explicitly. Others are in
        # "disabled" state.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers)
        self.assertTrue(all_with_status(CheckerState.enabled)
                        (cfg_handler.checks(), default_profile))
        self.assertTrue(all_with_status(CheckerState.disabled)
                        (cfg_handler.checks(), security_profile_alpha))

        # "--enable-all" leaves alpha checkers in "disabled" state. Others
        # become enabled.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers, enable_all=True)
        self.assertTrue(all_with_status(CheckerState.disabled)
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

        # Test if statisticsbased checkers are enabled by --stats flag
        # by default.
        stats_capable = bool(util.strtobool(
            os.environ.get('CC_TEST_FORCE_STATS_CAPABLE', 'False')))

        if stats_capable:
            cfg_handler = ClangSA.construct_config_handler(
                Namespace(stats_enabled=True))
            cfg_handler.initialize_checkers(checkers, [])

            enabled_checkers = (
                checker for checker, (enabled, _)
                in cfg_handler.checks().items()
                if enabled == CheckerState.enabled)

            for stat_checker in statisticsbased:
                self.assertTrue(
                    any(stat_checker in c for c in enabled_checkers))


class MockClangTidyCheckerLabels:
    def checkers_by_labels(self, labels):
        if labels[0] == 'profile:default':
            return [
                'bugprone-assert-side-effect',
                'bugprone-dangling-handle',
                'bugprone-inaccurate-erase']

    def get_description(self, label):
        if label == 'profile':
            return ['default', 'sensitive', 'security', 'portability',
                    'extreme']

    def occurring_values(self, label):
        if label == 'guideline':
            return ['sei-cert']
        elif label == 'sei-cert':
            return ['rule1', 'rule2']


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
        context = analyzer_context.get_context()
        context._checker_labels = MockClangTidyCheckerLabels()

        analyzer = create_analyzer_tidy()
        result_handler = create_result_handler(analyzer)
        cls.cmd = analyzer.construct_analyzer_cmd(result_handler)
        print('Analyzer command: %s' % cls.cmd)

    def _enable_disable_pos(self, checker, checks_list):
        """
        This function returns the positions of the patterns in "clang-tidy
        -checks=..." flag where the given checker has been enabled and disabled
        respectively. For example:

        clang-tidy -checks=-*,a,b*,-c

        "a": enabled->1, disabled->0
        "b": enabled->2, disabled->0
        "bx": enabled->2, disabled->0
        "c": enabled->-1, disabled->3

        If "enabled" position is greater than "disabled" position then the
        checker itself is enabled.
        """
        def checker_matches(pattern, checker):
            return bool(re.match(pattern.replace('*', '.*') + '$', checker))

        enable_pos = next((
            i for i, c in enumerate(checks_list) if
            checker_matches(c, checker)), -1)
        disable_pos = next(reversed([
            i for i, c in enumerate(checks_list) if
            checker_matches(c, '-' + checker)]), -1)

        return enable_pos, disable_pos

    def _is_disabled(self, checker, analyzer_cmd):
        """
        Returns True if the "checker" is disabled for clang-tidy given the
        analyzer command.
        """
        checks = next(filter(
            lambda arg: arg.startswith('-checks='),
            analyzer_cmd), None)

        if not checks:
            return True

        enable, disable = self._enable_disable_pos(
            checker,
            checks[len('-checks='):].split(','))

        return enable < disable

    def test_disable_clangsa_checkers(self):
        """
        Test that checker config still disables clang-analyzer-*.
        """
        analyzer = create_analyzer_tidy()
        result_handler = create_result_handler(analyzer)

        self.assertTrue(self._is_disabled(
            'clang-analyzer',
            analyzer.construct_analyzer_cmd(result_handler)))

        analyzer.config_handler.checker_config = \
            '{"Checks": "hicpp-use-nullptr"}'

        self.assertTrue(self._is_disabled(
            'clang-analyzer',
            analyzer.construct_analyzer_cmd(result_handler)))

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
        checker_labels = MockClangTidyCheckerLabels()

        for checker in checker_labels.checkers_by_labels(['profile:default']):
            self.assertFalse(self._is_disabled(
                checker, self.__class__.cmd))

    def test_clangsa_analyzer_checks_are_disabled(self):
        """
        Test that the clang-analyzer group is disabled in Clang Tidy.
        """
        self.assertTrue(self._is_disabled(
            'clang-analyzer', self.__class__.cmd))

    def test_clang_diags_as_compiler_warnings(self):
        """
        Test that clang-diagnostic-* checkers are enabled as compiler warnings.
        """

        args = Namespace()
        args.ordered_checkers = [
            # This should enable -Wvla and -Wvla-extension.
            ('clang-diagnostic-vla', True),
            ('clang-diagnostic-unused-value', False)
        ]
        analyzer = create_analyzer_tidy(args)
        result_handler = create_result_handler(analyzer)

        analyzer.config_handler.checker_config = '{}'
        analyzer.config_handler.analyzer_config = \
            {'take-config-from-directory': 'true'}

        cmd = analyzer.construct_analyzer_cmd(result_handler)

        # We expect that the clang-diagnostic-vla
        # and clang-diagnostic-vla-extension is enabled as -Wvla and
        # -Wvla-extension. The clang-diagnostic-unused-value is disabled as
        # -Wno-unused-value.
        self.assertEqual(cmd.count('-Wvla'), 1)
        self.assertEqual(cmd.count('-Wvla-extension'), 1)
