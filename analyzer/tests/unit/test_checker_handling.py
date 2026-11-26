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


from codechecker_common.util import strtobool
import os
import re
import shutil
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

from semver.version import Version

from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA
from codechecker_analyzer.analyzers.clangtidy.analyzer import ClangTidy
from codechecker_analyzer.analyzers.cppcheck.analyzer import Cppcheck
from codechecker_analyzer.analyzers.config_handler import CheckerState
from codechecker_analyzer.analyzers.clangtidy.config_handler \
    import ClangTidyConfigHandler
from codechecker_analyzer.arg import AnalyzerConfigArg, CheckerConfigArg, \
    analyzer_config
from codechecker_analyzer.cli.analyze import \
    is_analyzer_config_valid, is_checker_config_valid

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.buildlog import log_parser
import codechecker_analyzer.analyzer

from libtest.cmd_line import create_analyze_argparse


class MockClangsaCheckerLabels:
    def checkers_by_labels(self, labels):
        if labels[0] == 'profile:default':
            return ['deadcode.DeadStores', 'security.FloatLoopCounter']

        if labels[0] == 'prefix:security':
            return ['security.insecureAPI.bzero',
                    'security.insecureAPI.getpw']

        if labels[0] == 'profile:security':
            return ['alpha.security.ArrayBound',
                    'alpha.security.MallocOverflow']

        if labels[0] == 'profile:sensitive':
            return ['alpha.core.BoolAssignment',
                    'alpha.core.TestAfterDivZero']

        if labels[0] == 'guideline:sei-cert-c':
            return ['alpha.core.CastSize', 'alpha.core.CastToStruct']

        if labels[0] == 'severity:LOW':
            return ['security.insecureAPI.bcmp', 'alpha.llvm.Conventions']

        return []

    def get_description(self, label):
        if label == 'profile':
            return {
                "default": "",
                "sensitive": "",
                "security": "",
                "portability": "",
                "extreme": ""
            }
        return {}

    def occurring_values(self, label):
        if label == 'guideline':
            return ['sei-cert-c']
        elif label == 'sei-cert-c':
            return ['rule1', 'rule2']
        elif label == 'profile':
            return ['default',
                    'sensitive',
                    'security',
                    'portability',
                    'extreme']
        elif label == 'severity':
            return ['CRITICAL',
                    'HIGH',
                    'MEDIUM',
                    'LOW',
                    'STYLE',
                    'UNSPECIFIED']

        return []

    def checkers(self, _=None):
        return []


def create_analyzer_sa():
    cfg_handler = ClangSA.construct_config_handler(create_analyze_argparse())

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
        self.assertFalse(
            any(arg.startswith('-analyzer-disable-checker')
                for arg in self.__class__.cmd))

    def test_clangsa_checker_initializer(self):
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

        args = create_analyze_argparse()

        # "security" profile, but alpha -> not in default.
        security_profile_alpha = [
                'alpha.security.ArrayBound',
                'alpha.security.MallocOverflow']

        # "security" checker prefix group
        security_prefix = [
            'security.insecureAPI.bzero',
            'security.insecureAPI.getpw'
        ]

        # "sensitive" profile, but alpha -> not in default.
        sensitive_profile_alpha = [
                    'alpha.core.BoolAssignment',
                    'alpha.core.TestAfterDivZero']

        # "default" profile.
        default_profile = [
                'security.FloatLoopCounter',
                'deadcode.DeadStores']

        # Checkers covering some "sei-cert-c" rules.
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
        checkers.extend(map(add_description, security_prefix))
        checkers.extend(map(add_description, sensitive_profile_alpha))
        checkers.extend(map(add_description, default_profile))
        checkers.extend(map(add_description, cert_guideline))
        checkers.extend(map(add_description, statisticsbased))

        # "default" profile checkers are enabled explicitly. Others are in
        # "disabled" state.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers)
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), security_profile_alpha))

        # "--enable-all" leaves alpha checkers in "disabled" state. Others
        # become enabled.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers, enable_all=True)
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable alpha checkers explicitly with prefix label.
        # Using the "prefix" label is optional in this case, because the
        # checker group name "alpha" does not conflict with any checker
        # profiles or guidelines.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('prefix:alpha', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable alpha checkers explicitly.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('alpha', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable checkers of the "security" checker prefix group.
        # Using the "prefix" label is mandatory in this case, because the
        # checker group name "security" conflicts with a profile name.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('prefix:security', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), security_prefix))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable "security" profile checkers.
        # Using the "profile" label is mandatory in this case, because the
        # profile name "security" conflicts with a checker group name.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('profile:security', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), security_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable "security" profile checkers without "profile:" prefix.
        # This should throw an error, because the profile name "security"
        # conflicts with a checker group name.
        cfg_handler = ClangSA.construct_config_handler(args)
        with self.assertRaises(SystemExit) as e:
            cfg_handler.initialize_checkers(checkers,
                                            [('security', True)])
        self.assertEqual(e.exception.code, 1)

        # Enable "sensitive" profile checkers with the "profile:" label.
        # Using the "profile" label is optional in this case, because the
        # profile name "sensitive" does not conflict with any checker
        # prefix group names.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('profile:sensitive', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), sensitive_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable "sensitive" profile checkers without the "profile:" label.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('sensitive', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), sensitive_profile_alpha))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable "sei-cert-c" guideline checkers with the "guideline:" label.
        # Using the "guideline" label is optional in this case, because the
        # guideline name "sei-cert-c" does not conflict with any checker
        # prefix group names.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('guideline:sei-cert-c', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), cert_guideline))

        # Enable "sei-cert-c" guideline checkers without the "guideline:"
        # label.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('sei-cert-c', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), cert_guideline))

        # Disable "sei-cert-c" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('guideline:sei-cert-c', False)])
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), cert_guideline))

        # Disable "sei-cert-c" guideline checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('sei-cert-c', False)])
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), cert_guideline))

        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('default', False),
                                         ('DeadStores', True)])
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), default_profile))

        # Enable "LOW" severity checkers.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('severity:LOW', True)])
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), low_severity))

        # Enable checkers with a checker group prefix.
        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('default', False),
                                         ('cplusplus.NewDelete', True)])
        self.assertTrue(
            all_with_status(CheckerState.ENABLED)
            (cfg_handler.checks(), ['cplusplus.NewDelete']))
        self.assertTrue(
            all_with_status(CheckerState.DISABLED)
            (cfg_handler.checks(), ['cplusplus.NewDeleteLeaks']))

        cfg_handler = ClangSA.construct_config_handler(args)
        cfg_handler.initialize_checkers(checkers,
                                        [('default', False),
                                         ('cplusplus', True)])
        self.assertTrue(
            all_with_status(CheckerState.ENABLED)
            (cfg_handler.checks(), ['cplusplus.NewDelete',
                                    'cplusplus.NewDeleteLeaks']))

        # Test if statisticsbased checkers are enabled by --stats flag
        # by default.
        stats_capable = strtobool(
            os.environ.get('CC_TEST_FORCE_STATS_CAPABLE', 'False')
        )

        if stats_capable:
            cfg_handler = ClangSA.construct_config_handler(
                Namespace(stats_enabled=True))
            cfg_handler.initialize_checkers(checkers, [])

            enabled_checkers = (
                checker for checker, (enabled, _)
                in cfg_handler.checks().items()
                if enabled == CheckerState.ENABLED)

            for stat_checker in statisticsbased:
                self.assertTrue(
                    any(stat_checker in c for c in enabled_checkers))


class MockClangTidyCheckerLabels:
    def checkers_by_labels(self, labels, _=None):
        if labels[0] == 'profile:default':
            return [
                'bugprone-assert-side-effect',
                'bugprone-dangling-handle',
                'bugprone-inaccurate-erase',
                'clang-diagnostic-format',
                'clang-diagnostic-format-nonliteral',
                'clang-diagnostic-format-security']

        return []

    def get_description(self, label):
        if label == 'profile':
            return {
                "default": "",
                "sensitive": "",
                "security": "",
                "portability": "",
                "extreme": ""
            }
        return {}

    def occurring_values(self, label):
        if label == 'guideline':
            return ['sei-cert-c']
        elif label == 'sei-cert-c':
            return ['rule1', 'rule2']
        elif label == 'profile':
            return ['default',
                    'sensitive',
                    'security',
                    'portability',
                    'extreme']

        return []


def create_analyzer_tidy(args=None):
    cfg_handler = ClangTidy.construct_config_handler(
        create_analyze_argparse(args))

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
        print(f'Analyzer command: {cls.cmd}')

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

    def test_clangtidy_checker_initializer(self):
        """
        Test initialize_checkers() function.
        """
        def all_with_status(status):
            def f(checks, checkers):
                result = set(check for check, data in checks.items()
                             if data[0] == status)
                return set(checkers) <= result
            return f

        checkers = ClangTidy.get_analyzer_checkers()

        format_prefix = "clang-diagnostic-format"

        format_matched_default_checkers = [
            "clang-diagnostic-format-nonliteral",
            "clang-diagnostic-format-security"
        ]

        format_matched_not_default_checkers = [
            "clang-diagnostic-format-non-iso",
            "clang-diagnostic-format-pedantic",
        ]

        cfg_handler = ClangTidyConfigHandler()

        # Check the ambiguous option handling.
        with self.assertLogs(level='ERROR') as log:
            with self.assertRaises(SystemExit) as e:
                cfg_handler.initialize_checkers(checkers,
                                                [("clang-diagnostic-format",
                                                  True)])

        err_ambiguous_checker = re.compile(
            r"ERROR:.*?is ambiguous\. Please select one of these options to "
            r"clarify the checker list:.*$")

        match = err_ambiguous_checker.search(log.output[0])

        self.assertIsNotNone(match)
        self.assertEqual(e.exception.code, 1)

        # Check if the specified checker and the default checkers are enabled
        # when the clang-diagnostic-format is enabled by 'checker:' namespace.
        cfg_handler.initialize_checkers(checkers,
                                        [(f"checker:{format_prefix}", True)])
        self.assertIn(format_prefix, cfg_handler.checks())
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), [format_prefix]))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(),
                         format_matched_default_checkers))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(),
                         format_matched_not_default_checkers))

        # Check if the specified checker is the only one that enabled when the
        # clang-diagnostic-format is enabled by 'checker:' namespace and the
        # default profile is disabled.
        cfg_handler.initialize_checkers(checkers,
                                        [("default", False),
                                         (f"checker:{format_prefix}", True)])
        self.assertIn(format_prefix, cfg_handler.checks())
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), [format_prefix]))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(),
                         format_matched_default_checkers))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(),
                         format_matched_not_default_checkers))

        # Check if the specified checker is disabled by 'checker:' namespace
        # but the default profile is enabled.
        cfg_handler.initialize_checkers(checkers,
                                        [(f"checker:{format_prefix}", False)])
        self.assertIn(format_prefix, cfg_handler.checks())
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), [format_prefix]))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(),
                         format_matched_default_checkers))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(),
                         format_matched_not_default_checkers))

        # Check the prefix matched chackers when the 'prefix:' namespace
        # enables them.
        cfg_handler.initialize_checkers(checkers,
                                        [(f"prefix:{format_prefix}", True)])
        self.assertIn(format_prefix, cfg_handler.checks())
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(), [format_prefix]))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(),
                         format_matched_default_checkers))
        self.assertTrue(all_with_status(CheckerState.ENABLED)
                        (cfg_handler.checks(),
                         format_matched_not_default_checkers))

        # Check the prefix matched chackers when the 'prefix:' namespace
        # disables them.
        cfg_handler.initialize_checkers(checkers,
                                        [(f"prefix:{format_prefix}", False)])
        self.assertIn(format_prefix, cfg_handler.checks())
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(), [format_prefix]))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(),
                         format_matched_default_checkers))
        self.assertTrue(all_with_status(CheckerState.DISABLED)
                        (cfg_handler.checks(),
                         format_matched_not_default_checkers))

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
            '{"Checks": "modernize-use-nullptr"}'

        self.assertTrue(self._is_disabled(
            'clang-analyzer',
            analyzer.construct_analyzer_cmd(result_handler)))

        analyzer = create_analyzer_tidy(['--enable', 'Wreserved-id-macro'])
        result_handler = create_result_handler(analyzer)

        analyzer.config_handler.checker_config = '{}'
        analyzer.config_handler.analyzer_config = \
            {'take-config-from-directory': 'true'}

        for arg in analyzer.construct_analyzer_cmd(result_handler):
            self.assertFalse(arg.startswith('-checks'))

        self.assertNotIn("Wreserved-id-macro",
                         analyzer.config_handler.checks().keys())

    def test_analyze_correct_analyzer_not_enabled(self):
        """
        This test checks if an analyzer is not enabled but a config
        for it is getting set.
        """

        args = create_analyze_argparse()
        args.analyzers = ["gcc"]

        analyzer_cfg = [AnalyzerConfigArg(
            'clangsa', 'faux-bodies', 'false')]

        self.assertFalse(is_analyzer_config_valid(args, analyzer_cfg))

    def test_analyze_wrong_parameters(self):
        """
        This test checks whether the analyze command detects if a wrong
        --analyzer-config or --checker-config parameter is specified.
        """

        args = create_analyze_argparse()
        args.analyzers = ["clangsa", "clang-tidy"]

        analyzer_cfg_valid = [AnalyzerConfigArg(
            'clangsa', 'faux-bodies', 'false')]
        checker_cfg_valid = [CheckerConfigArg(
            'clang-tidy', 'performance-unnecessary-value-param',
            'IncludeStyle', 'false')]

        self.assertTrue(is_analyzer_config_valid(args, analyzer_cfg_valid))
        self.assertTrue(is_checker_config_valid(checker_cfg_valid))

        analyzer_cfg_invalid_analyzer = [AnalyzerConfigArg(
            'asd', 'faux-bodies', 'false')]
        analyzer_cfg_invalid_conf = [AnalyzerConfigArg(
            'clangsa', 'asd', 'false')]
        checker_cfg_invalid_analyzer = [CheckerConfigArg(
            'asd', 'performance-unnecessary-value-param',
            'IncludeStyle', 'false')]
        checker_cfg_invalid_checker = [CheckerConfigArg(
            'clang-tidy', 'asd',
            'IncludeStyle', 'false')]
        checker_cfg_invalid_checker_option = [CheckerConfigArg(
            'clang-tidy', 'performance-unnecessary-value-param',
            'asd', 'false')]

        self.assertFalse(is_analyzer_config_valid(
            args,
            analyzer_cfg_invalid_analyzer))
        self.assertFalse(
            is_analyzer_config_valid(args, analyzer_cfg_invalid_conf))

        self.assertFalse(is_checker_config_valid(checker_cfg_invalid_analyzer))
        self.assertFalse(is_checker_config_valid(checker_cfg_invalid_checker))
        self.assertFalse(is_checker_config_valid(
            checker_cfg_invalid_checker_option))

    def test_enable_all_disable_warning(self):
        """
        If --enable-all is used and a warning is disabled, then the proper
        parameterization of clang-tidy is using both -Weverything and
        -Wno-<warning> in this order.
        Side note: we use -Weverything instead of listing all enabled warnings
        to represent --enable-all.
        """
        analyzer = create_analyzer_tidy([
            '--enable-all',
            '--disable', 'clang-diagnostic-unused-variable'])
        result_handler = create_result_handler(analyzer)

        analyzer_cmd = analyzer.construct_analyzer_cmd(result_handler)

        try:
            pos_everything = analyzer_cmd.index('-Weverything')
            pos_disable = analyzer_cmd.index('-Wno-unused-variable')
            self.assertLess(pos_everything, pos_disable)
        except ValueError:
            # pylint: disable=redundant-unittest-assert
            self.assertFalse(
                False,
                "-Weverything and -Wno-unused-variable should be in the "
                "analysis command.")

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

        analyzer = create_analyzer_tidy([
            # This should enable -Wvla and -Wvla-extension.
            '--enable', 'prefix:clang-diagnostic-vla',
            '--disable', 'clang-diagnostic-unused-value'])
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


@unittest.skipIf(shutil.which('clang-tidy') is None,
                 "clang-tidy is not available")
class ClangTidyAllowNoChecksTest(unittest.TestCase):
    """
    With no -checks passed, clang-tidy 19+ errors on an empty check set, so
    --allow-no-checks must be added for those versions only.
    """

    @classmethod
    def setUpClass(cls):
        context = analyzer_context.get_context()
        context._checker_labels = MockClangTidyCheckerLabels()

    def _cmd_with(self, version):
        analyzer = create_analyzer_tidy()
        result_handler = create_result_handler(analyzer)
        with mock.patch.object(ClangTidy, 'get_checker_list',
                               return_value=([], [])), \
                mock.patch.object(ClangTidy, 'get_binary_version',
                                  return_value=version):
            return analyzer.construct_analyzer_cmd(result_handler)

    def test_added_for_tidy_19(self):
        cmd = self._cmd_with(Version.parse('19.1.0'))
        self.assertIn('--allow-no-checks', cmd)

    def test_not_added_for_tidy_18(self):
        cmd = self._cmd_with(Version.parse('18.1.8'))
        self.assertNotIn('--allow-no-checks', cmd)

    def test_not_added_when_version_unknown(self):
        cmd = self._cmd_with(None)
        self.assertNotIn('--allow-no-checks', cmd)


class ClangTidyTakeConfigFromDirectoryTest(unittest.TestCase):
    """
    With 'take-config-from-directory=true' the checkers are described by the
    '.clang-tidy' files, so CodeChecker must not configure the checkers of
    clang-tidy and must not rely on its own checker states either.
    """

    @classmethod
    def setUpClass(cls):
        context = analyzer_context.get_context()
        context._checker_labels = MockClangTidyCheckerLabels()

    def setUp(self):
        # The resolved checkers are cached by directory.
        # pylint: disable=protected-access
        ClangTidy._ClangTidy__effective_checkers = {}

    def test_no_checker_config_in_command(self):
        """
        Neither the checker list nor the checker configuration is forwarded,
        so that the '.clang-tidy' files are the only source of them.
        """
        analyzer = create_analyzer_tidy([
            '--analyzer-config', 'clang-tidy:take-config-from-directory=true',
            '--disable', 'default'])
        result_handler = create_result_handler(analyzer)

        cmd = analyzer.construct_analyzer_cmd(result_handler)

        self.assertFalse(any(arg.startswith('-checks') for arg in cmd))
        self.assertFalse(any(arg.startswith('-config') for arg in cmd))

    def test_analyzer_is_not_disabled_without_enabled_checkers(self):
        """
        '--disable-all' leaves no enabled checker in the config handler, but
        the analysis must still be executed, because the checkers come from
        the '.clang-tidy' files. This is what makes enabling a dummy checker
        by hand unnecessary.
        """
        has_enabled_checker = getattr(
            codechecker_analyzer.analyzer, '__has_enabled_checker')

        cfg_handler = create_analyzer_tidy([
            '--analyzer-config', 'clang-tidy:take-config-from-directory=true',
            '--disable', 'default']).config_handler

        self.assertFalse(any(
            state == CheckerState.ENABLED
            for state, _ in cfg_handler.checks().values()))
        self.assertTrue(has_enabled_checker(cfg_handler))

    def test_analyzer_is_disabled_without_the_option(self):
        """
        Without the option the analyzer is still skipped when it has no
        enabled checker.
        """
        has_enabled_checker = getattr(
            codechecker_analyzer.analyzer, '__has_enabled_checker')

        cfg_handler = create_analyzer_tidy(
            ['--disable', 'default']).config_handler

        self.assertFalse(has_enabled_checker(cfg_handler))

    def test_effective_checkers_of_directory(self):
        """
        The checkers of a directory are queried from the analyzer binary.
        """
        list_checks_output = \
            "Enabled checks:\n" \
            "    bugprone-sizeof-expression\n" \
            "    clang-analyzer-core.NullDereference\n" \
            "    misc-unused-parameters\n\n"

        with mock.patch.object(ClangTidy, 'analyzer_binary',
                               return_value='clang-tidy'), \
                mock.patch('subprocess.check_output',
                           return_value=list_checks_output) as check_output:
            checkers = ClangTidy.get_effective_checkers_for_dir('/some/dir')

        # Clang Static Analyzer checkers are reported by clang-tidy too, but
        # they are not clang-tidy checkers.
        self.assertEqual(
            checkers,
            {'bugprone-sizeof-expression', 'misc-unused-parameters'})

        self.assertEqual(check_output.call_count, 1)
        self.assertEqual(
            check_output.call_args.kwargs['cwd'], os.path.abspath('/some/dir'))

    def test_effective_checkers_are_cached(self):
        """
        Every source file of a directory has the same configuration, so the
        analyzer binary is invoked only once per directory.
        """
        with mock.patch.object(ClangTidy, 'analyzer_binary',
                               return_value='clang-tidy'), \
                mock.patch('subprocess.check_output',
                           return_value="Enabled checks:\n    misc-const-"
                                        "correctness\n") as check_output:
            first = ClangTidy.get_effective_checkers_for_dir('/some/dir')
            second = ClangTidy.get_effective_checkers_for_dir('/some/dir')

        self.assertEqual(first, second)
        self.assertEqual(check_output.call_count, 1)

    def test_effective_checkers_of_checker_groups(self):
        """
        A '.clang-tidy' file may enable a whole checker group with a glob.
        The analyzer resolves these to concrete checker names, so no glob may
        appear among the returned checkers.
        """
        list_checks_output = \
            "Enabled checks:\n" \
            "    bugprone-assert-side-effect\n" \
            "    bugprone-sizeof-expression\n" \
            "    readability-braces-around-statements\n\n"

        with mock.patch.object(ClangTidy, 'analyzer_binary',
                               return_value='clang-tidy'), \
                mock.patch('subprocess.check_output',
                           return_value=list_checks_output):
            checkers = ClangTidy.get_effective_checkers_for_dir('/some/dir')

        self.assertEqual(
            checkers,
            {'bugprone-assert-side-effect',
             'bugprone-sizeof-expression',
             'readability-braces-around-statements'})
        self.assertFalse([c for c in checkers if '*' in c])

    def test_effective_checkers_of_failing_analyzer(self):
        """
        A failing analyzer invocation must not break the analysis.
        """
        with mock.patch.object(ClangTidy, 'analyzer_binary',
                               return_value='clang-tidy'), \
                mock.patch('subprocess.check_output',
                           side_effect=OSError("No such file")):
            checkers = ClangTidy.get_effective_checkers_for_dir('/some/dir')

        self.assertEqual(checkers, set())


def create_analyzer_cppcheck(args, workspace):
    cfg_handler = Cppcheck.construct_config_handler(args)

    action = {
        'file': 'main.cpp',
        'command': "g++ -o main main.cpp",
        'directory': workspace}
    build_action = log_parser.parse_options(action)

    return Cppcheck(cfg_handler, build_action)


class MockCppcheckCheckerLabels:
    def checkers_by_labels(self, labels, _=None):
        if labels[0] == 'profile:default':
            return [
                'cppcheck-argumentSize',
                'cppcheck-arrayIndexOutOfBounds',
                'cppcheck-assertWithSideEffect']

        return []

    def get_description(self, label):
        if label == 'profile':
            return {
                "default": "",
                "sensitive": "",
                "security": "",
                "portability": "",
                "extreme": ""
            }
        return {}

    def occurring_values(self, label):
        if label == 'guideline':
            return ['sei-cert-c']
        elif label == 'sei-cert-c':
            return ['rule1', 'rule2']
        elif label == 'profile':
            return ['default',
                    'sensitive',
                    'security',
                    'portability',
                    'extreme']

        return []

    def checkers(self, _):
        return []


class CheckerHandlingCppcheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        context = analyzer_context.get_context()
        context._checker_labels = MockCppcheckCheckerLabels()

    def test_cppcheckargs(self):
        """
        Check if the content of --cppcheckargs config file is properly passed
        to the analyzer command.
        """
        with tempfile.TemporaryDirectory() as tmp_ws:
            cppcheckargs = os.path.join(tmp_ws, 'cppcheckargs')
            with open(cppcheckargs, 'w',
                      encoding='utf-8', errors='ignore') as f:
                f.write('--max-ctu-depth=42')

            args = Namespace()
            args.analyzers = ["clang-tidy"]
            args.analyzer_config = [analyzer_config(
                f"cppcheck:cc-verbatim-args-file={cppcheckargs}")]

            analyzer = create_analyzer_cppcheck(args, tmp_ws)
            result_handler = create_result_handler(analyzer)
            cmd = analyzer.construct_analyzer_cmd(result_handler)

            self.assertIn('--max-ctu-depth=42', cmd)
