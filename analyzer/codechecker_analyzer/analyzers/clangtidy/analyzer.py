# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
"""

import ast
import json
import os
import re
import shlex
import subprocess
from typing import List, Tuple

from codechecker_common.logger import get_logger

from codechecker_analyzer import env

from .. import analyzer_base
from ..config_handler import CheckerState, get_compiler_warning_name
from ..flag import has_flag
from ..flag import prepend_all

from . import config_handler
from . import result_handler

LOG = get_logger('analyzer')


def parse_checkers(tidy_output):
    """
    Parse clang tidy checkers list.
    Skip clang static analyzer checkers.
    Store them to checkers.
    """
    checkers = []
    pattern = re.compile(r'^\S+$')
    for line in tidy_output.splitlines():
        line = line.strip()
        if line.startswith('Enabled checks:') or line == '':
            continue
        elif line.startswith('clang-analyzer-'):
            continue
        match = pattern.match(line)
        if match:
            checkers.append((match.group(0), ''))
    return checkers


def parse_checker_config(config_dump):
    """
    Return the parsed clang-tidy config options as a list of
    (flag, default_value) tuples.
    config_dump -- clang-tidy config options YAML dump.
    """
    reg = re.compile(r'key:\s+(\S+)\s+value:\s+([^\n]+)')
    return re.findall(reg, config_dump)


def parse_analyzer_config(config_dump):
    """
    Return the parsed clang-tidy analyzer options as a list of
    (flag, default_value) tuples.
    config_dump -- clang-tidy config options YAML dump.
    """
    return re.findall(r'^(\S+):\s+(\S+)$', config_dump, re.MULTILINE)


class ClangTidy(analyzer_base.SourceAnalyzer):
    """
    Constructs the clang tidy analyzer commands.
    """

    ANALYZER_NAME = 'clang-tidy'

    def add_checker_config(self, checker_cfg):
        LOG.error("Not implemented yet")

    @classmethod
    def get_analyzer_checkers(cls, cfg_handler, environ):
        """
        Return the list of the all of the supported checkers.
        """
        try:
            result = subprocess.check_output(
                [cfg_handler.analyzer_binary, "-list-checks", "-checks=*"],
                env=environ,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
            return parse_checkers(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    @classmethod
    def get_checker_config(cls, cfg_handler, environ):
        """
        Return the checker configuration of the all of the supported checkers.
        """
        try:
            result = subprocess.check_output(
                [cfg_handler.analyzer_binary, "-dump-config", "-checks=*"],
                env=environ,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
            return parse_checker_config(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    @classmethod
    def get_analyzer_config(cls, cfg_handler, environ):
        """
        Return the analyzer configuration with all checkers enabled.
        """
        try:
            result = subprocess.check_output(
                [cfg_handler.analyzer_binary, "-dump-config", "-checks=*"],
                env=environ,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
            return parse_analyzer_config(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    def get_checker_list(self, config) -> Tuple[List[str], List[str]]:
        """
        Return a list of checkers and warnings what needs to be enabled during
        analysis.

        If the file specified by the '--tidy-config' option contains a 'Checks'
        key or the 'Checks' option is specified through the '--analyzer-config'
        the return value will be a tuple of empty lists which means do not turn
        checkers explicitly. "clang-analyzer-*" is an exception, because we
        want to disable these even if analyzer config is given. If we wouldn't
        disable this group then some ClangSA checkers would be invoked by
        clang-tidy and in some cases that would cause analysis error due to
        some ClangSA bug.
        """
        checkers = []
        compiler_warnings = []

        has_checker_config = \
            config.checker_config and config.checker_config != '{}'

        # Do not disable any clang-tidy checks explicitly, but don't run
        # ClangSA checkers. ClangSA checkers are driven by an other
        # analyzer in CodeChecker.
        checkers.append('-clang-analyzer-*')

        # For clang compiler warnings a correspoding
        # clang-diagnostic error is generated by Clang tidy.
        # They can be disabled by this glob -clang-diagnostic-*
        checkers.append('clang-diagnostic-*')

        # Config handler stores which checkers are enabled or disabled.
        for checker_name, value in config.checks().items():
            state, _ = value

            # Checker name is a compiler warning.
            warning_name = get_compiler_warning_name(checker_name)
            if warning_name is not None:
                if state == CheckerState.enabled:
                    compiler_warnings.append('-W' + warning_name)
                elif state == CheckerState.disabled:
                    compiler_warnings.append('-Wno-' + warning_name)

                continue
            elif checker_name.startswith('clang-diagnostic'):
                checker_name += '*'

            if state == CheckerState.enabled:
                checkers.append(checker_name)
            elif state == CheckerState.disabled:
                checkers.append('-' + checker_name)

        # -checks=-clang-analyzer-* option is added to the analyzer command by
        # default except when all analyzer config options come from .clang-tidy
        # file. The content of this file overrides every other custom config
        # that is specific to clang-tidy. Compiler warnings however are flags
        # for the compiler, clang-tidy is just capable to emit them in its own
        # format.
        if config.analyzer_config.get('take-config-from-directory') == 'true':
            return [], compiler_warnings

        if has_checker_config:
            try:
                # Is is possible that the value of config.checker_config
                # is not a valid JSON string because the keys/values are
                # quoted with single quotes instead of double quotes. For
                # this reason we can't use the json.loads function to parse
                # this string but we need to use 'literal_eval' function to
                # safely evaluate the expression which will be a
                # valid dictionary.
                checker_cfg = ast.literal_eval(config.checker_config.strip())
                if checker_cfg.get('Checks'):
                    return [], compiler_warnings
            except SyntaxError as ex:
                LOG.debug("Invalid checker configuration: %s. Error: %s",
                          config.checker_config, ex)

        return checkers, compiler_warnings

    def construct_analyzer_cmd(self, result_handler):
        """ Contruct command which will be executed on analysis. """
        try:
            config = self.config_handler

            analyzer_cmd = [config.analyzer_binary]

            checks, compiler_warnings = self.get_checker_list(config)

            if checks:
                # The invocation should end in a Popen call with shell=False,
                # so no globbing should occur even if the checks argument
                # contains characters that would trigger globbing in the shell.
                analyzer_cmd.append("-checks=%s" % ','.join(checks))

            analyzer_cmd.extend(config.analyzer_extra_arguments)

            if config.checker_config and config.checker_config != '{}':
                analyzer_cmd.append("-config=" + config.checker_config)

            analyzer_cmd.append(self.source_file)

            analyzer_cmd.extend(['--export-fixes', result_handler.fixit_file])

            analyzer_cmd.append("--")

            analyzer_cmd.append('-Qunused-arguments')

            # Enable these compiler warnings by default.
            analyzer_cmd.extend(['-Wall', '-Wextra'])

            compile_lang = self.buildaction.lang

            if not has_flag('-x', analyzer_cmd):
                analyzer_cmd.extend(['-x', compile_lang])

            if not has_flag('--target', analyzer_cmd) and \
                    self.buildaction.target != "":
                analyzer_cmd.append(f"--target={self.buildaction.target}")

            if not has_flag('-arch', analyzer_cmd) and \
                    self.buildaction.arch != "":
                analyzer_cmd.extend(["-arch ", self.buildaction.arch])

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.extend(prepend_all(
                '-isystem',
                self.buildaction.compiler_includes))

            if not has_flag('-std', analyzer_cmd) and not \
                    has_flag('--std', analyzer_cmd):
                analyzer_cmd.append(self.buildaction.compiler_standard)

            analyzer_cmd.extend(compiler_warnings)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    def get_analyzer_mentioned_files(self, output):
        """
        Parse Clang-Tidy's output to generate a list of files that were
        mentioned in the standard output or standard error.
        """

        if not output:
            return set()

        # A line mentioning a file in Clang-Tidy's output looks like this:
        # /home/.../.cpp:L:C: warning: foobar.
        regex = re.compile(
            # File path followed by a ':'.
            r'^(?P<path>[\S ]+?):'
            # Line number followed by a ':'.
            r'(?P<line>\d+?):'
            # Column number followed by a ':' and a space.
            r'(?P<column>\d+?): ')

        paths = []

        for line in output.splitlines():
            match = re.match(regex, line)
            if match:
                paths.append(match.group('path'))

        return set(paths)

    @classmethod
    def resolve_missing_binary(cls, configured_binary, environ):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

        LOG.debug("%s not found in path for ClangTidy!", configured_binary)

        if os.path.isabs(configured_binary):
            # Do not autoresolve if the path is an absolute path as there
            # is nothing we could auto-resolve that way.
            return False

        # clang-tidy, clang-tidy-5.0, ...
        clangtidy = env.get_binary_in_path(['clang-tidy'],
                                           r'^clang-tidy(-\d+(\.\d+){0,2})?$',
                                           environ)

        if clangtidy:
            LOG.debug("Using '%s' for Clang-tidy!", clangtidy)
        return clangtidy

    @classmethod
    def version_compatible(cls, configured_binary, environ):
        """
        Check the version compatibility of the given analyzer binary.
        """
        return True

    def construct_result_handler(self, buildaction, report_output,
                                 checker_labels, skiplist_handler):
        """
        See base class for docs.
        """
        report_hash = self.config_handler.report_hash
        res_handler = result_handler.ClangTidyResultHandler(
            buildaction, report_output, report_hash)

        res_handler.checker_labels = checker_labels
        res_handler.skiplist_handler = skiplist_handler
        return res_handler

    @classmethod
    def construct_config_handler(cls, args, context):
        handler = config_handler.ClangTidyConfigHandler()
        handler.analyzer_binary = context.analyzer_binaries.get(
            cls.ANALYZER_NAME)
        handler.report_hash = args.report_hash \
            if 'report_hash' in args else None

        # FIXME We cannot get the resource dir from the clang-tidy binary,
        # therefore we get a sibling clang binary which of clang-tidy.
        # TODO Support "clang-tidy -print-resource-dir" .
        check_env = env.extend(context.path_env_extra,
                               context.ld_lib_path_extra)
        # Overwrite PATH to contain only the parent of the clang binary.
        if os.path.isabs(handler.analyzer_binary):
            check_env['PATH'] = os.path.dirname(handler.analyzer_binary)
        try:
            with open(args.tidy_args_cfg_file, 'r', encoding='utf-8',
                      errors='ignore') as tidy_cfg:
                handler.analyzer_extra_arguments = \
                    re.sub(r'\$\((.*?)\)', env.replace_env_var,
                           tidy_cfg.read().strip())
                handler.analyzer_extra_arguments = \
                    shlex.split(handler.analyzer_extra_arguments)
        except IOError as ioerr:
            LOG.debug_analyzer(ioerr)
        except AttributeError as aerr:
            # No clang tidy arguments file was given in the command line.
            LOG.debug_analyzer(aerr)

        analyzer_config = {}
        # TODO: This extra "isinstance" check is needed for
        # CodeChecker analyzers --analyzer-config. This command also
        # runs this function in order to construct a config handler.
        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            r = re.compile(r'(?P<analyzer>.+?):(?P<key>.+?)=(?P<value>.+)')
            for cfg in args.analyzer_config:
                m = re.search(r, cfg)
                if m.group('analyzer') == cls.ANALYZER_NAME:
                    analyzer_config[m.group('key')] = m.group('value')

        # If both --analyzer-config and -config (in --tidyargs) is given then
        # these need to be merged. Since "HeaderFilterRegex" has a default
        # value in --analyzer-config, we take --tidyargs stronger so user can
        # overwrite its value.
        for i, extra_arg in enumerate(handler.analyzer_extra_arguments):
            if not extra_arg.startswith('-config'):
                continue

            # -config flag can be together or separate from its argument:
            # "-config blabla" vs. "-config=blabla"
            if extra_arg == '-config':
                arg = handler.analyzer_extra_arguments[i + 1]
                arg_num = 2
            else:
                arg = extra_arg[len('-config='):]
                arg_num = 1

            analyzer_config.update(json.loads(arg))
            del handler.analyzer_extra_arguments[i:i + arg_num]
            break

        # TODO: This extra "isinstance" check is needed for
        # CodeChecker checkers --checker-config. This command also
        # runs this function in order to construct a config handler.
        if 'checker_config' in args and isinstance(args.checker_config, list):
            r = re.compile(r'(?P<analyzer>.+?):(?P<key>.+?)=(?P<value>.+)')
            check_options = []

            for cfg in args.checker_config:
                m = re.search(r, cfg)
                if m.group('analyzer') == cls.ANALYZER_NAME:
                    check_options.append({'key': m.group('key'),
                                          'value': m.group('value')})
            analyzer_config['CheckOptions'] = check_options
        else:
            try:
                with open(args.tidy_config, 'r',
                          encoding='utf-8', errors='ignore') as tidy_config:
                    handler.checker_config = tidy_config.read()
            except IOError as ioerr:
                LOG.debug_analyzer(ioerr)
            except AttributeError as aerr:
                # No clang tidy config file was given in the command line.
                LOG.debug_analyzer(aerr)

        handler.analyzer_config = analyzer_config

        # 'take-config-from-directory' is a special option which let the user
        # to use the '.clang-tidy' config files. It will disable analyzer and
        # checker configuration options.
        if not handler.checker_config and \
                analyzer_config.get('take-config-from-directory') != 'true':
            handler.checker_config = json.dumps(analyzer_config)

        check_env = env.extend(context.path_env_extra,
                               context.ld_lib_path_extra)

        checkers = ClangTidy.get_analyzer_checkers(handler, check_env)

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug_analyzer('No checkers were defined in '
                               'the command line for %s',
                               cls.ANALYZER_NAME)
            cmdline_checkers = []

        handler.initialize_checkers(
            context,
            checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        return handler
