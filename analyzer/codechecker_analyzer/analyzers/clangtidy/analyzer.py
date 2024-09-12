# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Module for handling ClangTidy-related functionality related to analysis,
checker handling and configuration.
"""

import ast
import json
import os
import re
import shlex
import subprocess
from typing import Iterable, List, Set, Tuple

import yaml

from codechecker_common.logger import get_logger

from codechecker_analyzer import analyzer_context, env
from codechecker_analyzer.analyzers.clangsa.analyzer import ClangSA

from .. import analyzer_base
from ..config_handler import CheckerState, CheckerType, \
    get_compiler_warning_name_and_type
from ..flag import has_flag
from ..flag import prepend_all

from . import config_handler
from . import result_handler as clangtidy_result_handler

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

        if line.startswith('clang-analyzer-'):
            continue

        match = pattern.match(line)
        if match:
            checkers.append((match.group(0), ''))
    return checkers


def parse_checker_config_old(config_dump):
    """
    Return the parsed clang-tidy config options as a list of
    (flag, default_value) tuples. This variant works
    for clang-tidy up to version 14.

    config_dump -- clang-tidy config options YAML dump in pre-LLVM15 format.
    """
    reg = re.compile(r'key:\s+(\S+)\s+value:\s+([^\n]+)')
    result = re.findall(reg, config_dump)
    # tidy emits the checker option with a "." prefix, but we need a ":"
    result = [(option[0].replace(".", ":"), option[1]) for option in result]
    return result


def parse_checker_config_new(config_dump):
    """
    Return the parsed clang-tidy config options as a list of
    (flag, default_value) tuples. This variant works
    for clang-tidy starting with version 15

    config_dump -- clang-tidy config options YAML dump in post-LLVM15 format.
    """
    try:
        data = yaml.safe_load(config_dump)
        if 'CheckOptions' not in data:
            return None

        return [[key.replace(".", ":"), value]
                for (key, value) in data['CheckOptions'].items()]
    except ImportError:
        return None


def parse_checker_config(config_dump):
    """
    Return the parsed clang-tidy config options as a list of
    (flag, default_value) tuples.
    config_dump -- clang-tidy config options YAML dump.
    """
    result = parse_checker_config_old(config_dump)
    if not result:
        result = parse_checker_config_new(config_dump)

    return result


def parse_analyzer_config(config_dump):
    """
    Return the parsed clang-tidy analyzer options as a list of
    (flag, default_value) tuples.
    config_dump -- clang-tidy config options YAML dump.
    """
    return re.findall(r'^(\S+):\s+(\S+)$', config_dump, re.MULTILINE)


def get_diagtool_bin():
    """
    Return full path of diagtool.

    Select clang binary, check for a 'diagtool' binary next to the selected
    clang binary and return full path of this binary if it exists.
    """
    context = analyzer_context.get_context()
    clang_bin = context.analyzer_binaries.get(ClangSA.ANALYZER_NAME)

    if not clang_bin:
        return None

    # Resolve symlink.
    clang_bin = os.path.realpath(clang_bin)

    # Find diagtool next to the clang binary.
    diagtool_bin = os.path.join(os.path.dirname(clang_bin), 'diagtool')
    if os.path.exists(diagtool_bin):
        return diagtool_bin

    LOG.warning(
        "'diagtool' can not be found next to the clang binary (%s)!",
        clang_bin)

    return None


def get_warnings():
    """
    Returns list of warning flags by using diagtool.
    """
    diagtool_bin = get_diagtool_bin()
    environment = analyzer_context.get_context().get_env_for_bin(diagtool_bin)

    if not diagtool_bin:
        return []

    try:
        result = subprocess.check_output(
            [diagtool_bin, 'tree'],
            env=environment,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore")
        return [w[2:] for w in result.split()
                if w.startswith("-W") and w != "-W"]
    except subprocess.CalledProcessError as exc:
        LOG.error("'diagtool' encountered an error while retrieving the "
                  "checker list. If you are using a custom compiled clang, "
                  "you may have forgotten to build the 'diagtool' target "
                  "alongside 'clang' and 'clang-tidy'! Error message: %s",
                  exc.output)

        raise


def _add_asterisk_for_group(
    subset_checkers: Iterable[str],
    all_checkers: Set[str]
) -> List[str]:
    """
    Since CodeChecker interprets checker name prefixes as checker groups, they
    have to be added a '*' joker character when using them at clang-tidy
    -checks flag. This function adds a '*' for each item in "checkers" if it's
    a checker group, i.e. identified as a prefix for any checker name in
    "all_checkers".
    For example "readability-container" is a prefix of multiple checkers, so
    this is converted to "readability-container-*". On the other hand
    "performance-trivially-destructible" is a full checker name, so it remains
    as is.
    """
    def is_group_prefix_of(prefix: str, long: str) -> bool:
        """
        Returns True if a checker(-group) name is prefix of another
        checker name. For example bugprone-string is prefix of
        bugprone-string-constructor but not of
        bugprone-stringview-nullptr.
        """
        prefix_split = prefix.split('-')
        long_split = long.split('-')
        return prefix_split == long_split[:len(prefix_split)]

    def need_asterisk(checker: str) -> bool:
        return any(
            is_group_prefix_of(checker, long) and checker != long
            for long in all_checkers)

    result = []

    for checker in subset_checkers:
        result.append(checker + ('*' if need_asterisk(checker) else ''))

    return result


def parse_version(tidy_output):
    """
    Parse clang-tidy version output and return the version number.
    """
    version_re = re.compile(r'.*version (?P<version>[\d\.]+)', re.S)
    match = version_re.match(tidy_output)
    if match:
        return match.group('version')
    return None


class ClangTidy(analyzer_base.SourceAnalyzer):
    """
    Constructs the clang tidy analyzer commands.
    """

    ANALYZER_NAME = 'clang-tidy'

    # Cache object for get_analyzer_checkers().
    __analyzer_checkers = None

    @classmethod
    def analyzer_binary(cls):
        return analyzer_context.get_context() \
            .analyzer_binaries[cls.ANALYZER_NAME]

    @classmethod
    def get_binary_version(cls, details=False) -> str:
        if not cls.analyzer_binary():
            return None
        # No need to LOG here, we will emit a warning later anyway.
        environ = analyzer_context.get_context().get_env_for_bin(
            cls.analyzer_binary())

        version = [cls.analyzer_binary(), '--version']
        try:
            output = subprocess.check_output(version,
                                             env=environ,
                                             universal_newlines=True,
                                             encoding="utf-8",
                                             errors="ignore")
            if details:
                return output.strip()
            return parse_version(output)
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: %s",
                        ' '.join(version))
            LOG.warning(oerr)

        return None

    def add_checker_config(self, _):
        LOG.error("Not implemented yet")

    @classmethod
    def get_analyzer_checkers(cls):
        """
        Return the list of the all of the supported checkers.
        """
        try:
            if cls.__analyzer_checkers:
                return cls.__analyzer_checkers

            environ = analyzer_context\
                .get_context().get_env_for_bin(cls.analyzer_binary())
            result = subprocess.check_output(
                [cls.analyzer_binary(), "-list-checks", "-checks=*"],
                env=environ,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
            checker_description = parse_checkers(result)

            checker_description.extend(
                ("clang-diagnostic-" + warning, "")
                for warning in get_warnings())

            cls.__analyzer_checkers = checker_description

            return checker_description
        except (subprocess.CalledProcessError, OSError):
            return []

    @classmethod
    def get_checker_config(cls):
        """
        Return the checker configuration of the all of the supported checkers.
        """
        try:
            result = subprocess.check_output(
                [cls.analyzer_binary(), "-dump-config", "-checks=*"],
                env=analyzer_context.get_context()
                .get_env_for_bin(cls.analyzer_binary()),
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
            return parse_checker_config(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    @classmethod
    def get_analyzer_config(cls):
        """
        Return the analyzer configuration with all checkers enabled.
        """
        if not cls.analyzer_binary():
            return []

        try:
            result = subprocess.check_output(
                [cls.analyzer_binary(), "-dump-config", "-checks=*"],
                env=analyzer_context.get_context()
                .get_env_for_bin(cls.analyzer_binary()),
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

        If 'Checks' option is specified through '--analyzer-config'
        the return value will be a tuple of empty lists which means do not turn
        checkers explicitly. "clang-analyzer-*" is an exception, because we
        want to disable these even if analyzer config is given. If we wouldn't
        disable this group then some ClangSA checkers would be invoked by
        clang-tidy and in some cases that would cause analysis error due to
        some ClangSA bug.
        """
        # clang-tidy emits reports from its check in the same format as
        # compiler diagnostics (like unused variables, etc). This makes it a
        # little difficult to distinguish compiler warnings and clang-tidy
        # check warnings. The only clue is that compiler warnings are emitted
        # as if they came from a check called clang-diagnostic- (e.g.
        # -Wunused-variable will emit a warning under the name
        # clang-diagnostic-unused-variable).

        # There are two ways to disable a compiler warning in clang-tidy,
        # either by -Wno- or -checks=-clang-diagnostic- (note the dash before
        # clang-diagnostic!). However, there is only one way to enable them:
        # through -W. Using -checks=clang-diagnostic- does not enable the
        # warning, but undoes -checks=-clang-diagnostic-.

        # Since we disable all checks by default via -checks=-*, in order to
        # enable a compiler warning, we first have to undo the -checks level
        # disable and then enable it, so we need both
        # -checks=compiler-diagnostic- and -W.
        compiler_warnings = []
        enabled_checkers = []

        has_checker_config = \
            config.checker_config and config.checker_config != '{}'

        # Config handler stores which checkers are enabled or disabled.
        for checker_name, value in config.checks().items():
            state, _ = value

            warning_name, warning_type = \
                get_compiler_warning_name_and_type(checker_name)

            # This warning must be given a parameter separated by either '=' or
            # space. This warning is not supported as a checker name so its
            # special usage is avoided.
            if warning_name and warning_name.startswith('frame-larger-than'):
                continue

            if warning_name is not None:
                # -W and clang-diagnostic- are added as compiler warnings.
                if warning_type == CheckerType.COMPILER:
                    LOG.warning("As of CodeChecker v6.22, the following usage"
                                f"of '{checker_name}' compiler warning as a "
                                "checker name is deprecated, please use "
                                f"'clang-diagnostic-{checker_name[1:]}' "
                                "instead.")
                    if state == CheckerState.ENABLED:
                        compiler_warnings.append('-W' + warning_name)
                        enabled_checkers.append(checker_name)
                    elif state == CheckerState.DISABLED:
                        if config.enable_all:
                            LOG.warning("Disabling compiler warning with "
                                        f"compiler flag '-d W{warning_name}' "
                                        "is not supported.")
                # If a clang-diagnostic-... is enabled add it as a compiler
                # warning as -W..., if it is disabled, tidy can suppress when
                # specified in the -checks parameter list, so we add it there
                # as -clang-diagnostic-... .
                elif warning_type == CheckerType.ANALYZER:
                    if state == CheckerState.ENABLED:
                        if checker_name == "clang-diagnostic-error":
                            # Disable warning of clang-diagnostic-error to
                            # avoid generated compiler errors.
                            compiler_warnings.append('-Wno-' + warning_name)
                        else:
                            compiler_warnings.append('-W' + warning_name)
                        enabled_checkers.append(checker_name)
                    else:
                        compiler_warnings.append('-Wno-' + warning_name)

                continue

            if state == CheckerState.ENABLED:
                enabled_checkers.append(checker_name)

        # By default all checkers are disabled and the enabled ones are added
        # explicitly.
        checkers = ['-*']

        checkers += _add_asterisk_for_group(
            enabled_checkers,
            set(x[0] for x in ClangTidy.get_analyzer_checkers()))

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

            analyzer_cmd = [ClangTidy.analyzer_binary()]

            checks, compiler_warnings = self.get_checker_list(config)

            if checks:
                # The invocation should end in a Popen call with shell=False,
                # so no globbing should occur even if the checks argument
                # contains characters that would trigger globbing in the shell.
                analyzer_cmd.append(f"-checks={','.join(checks)}")

            analyzer_cmd.extend(config.analyzer_extra_arguments)

            if config.checker_config and config.checker_config != '{}':
                analyzer_cmd.append("-config=" + config.checker_config)

            analyzer_cmd.append(self.source_file)

            analyzer_cmd.extend(['--export-fixes', result_handler.fixit_file])

            analyzer_cmd.append("--")

            analyzer_cmd.append('-Qunused-arguments')

            # Enable these compiler warnings by default.
            if not config.enable_all:
                analyzer_cmd.extend(['-Wno-everything'])

            compile_lang = self.buildaction.lang

            if not has_flag('-x', analyzer_cmd):
                analyzer_cmd.extend(['-x', compile_lang])

            if not has_flag('--target', analyzer_cmd) and \
                    self.buildaction.target != "":
                analyzer_cmd.append(f"--target={self.buildaction.target}")

            if not has_flag('-arch', analyzer_cmd) and \
                    self.buildaction.arch != "":
                analyzer_cmd.extend(["-arch", self.buildaction.arch])

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.extend(prepend_all(
                '-isystem' if config.add_gcc_include_dirs_with_isystem else
                '-idirafter',
                self.buildaction.compiler_includes))

            if not has_flag('-std', analyzer_cmd) and not \
                    has_flag('--std', analyzer_cmd):
                analyzer_cmd.append(self.buildaction.compiler_standard)

            if config.enable_all:
                analyzer_cmd.append("-Weverything")
                analyzer_cmd.extend(
                    filter(lambda x: x.startswith('-Wno-'), compiler_warnings))
            else:
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
    def is_binary_version_incompatible(cls):
        """
        We support pretty much every Clang-Tidy version.
        """
        return None

    def construct_result_handler(self, buildaction, report_output,
                                 skiplist_handler):
        """
        See base class for docs.
        """
        report_hash = self.config_handler.report_hash
        res_handler = clangtidy_result_handler.ClangTidyResultHandler(
            buildaction, report_output, report_hash)

        res_handler.skiplist_handler = skiplist_handler
        return res_handler

    @classmethod
    def construct_config_handler(cls, args):
        handler = config_handler.ClangTidyConfigHandler()
        handler.report_hash = args.report_hash \
            if 'report_hash' in args else None

        handler.add_gcc_include_dirs_with_isystem = \
            'add_gcc_include_dirs_with_isystem' in args and \
            args.add_gcc_include_dirs_with_isystem

        # FIXME We cannot get the resource dir from the clang-tidy binary,
        # therefore we get a sibling clang binary which of clang-tidy.
        # TODO Support "clang-tidy -print-resource-dir" .
        try:
            with open(args.tidy_args_cfg_file, 'r', encoding='utf-8',
                      errors='ignore') as tidy_cfg:
                handler.analyzer_extra_arguments = \
                    re.sub(r'\$\((.*?)\)',
                           env.replace_env_var(args.tidy_args_cfg_file),
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
            for cfg in args.analyzer_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    analyzer_config[cfg.option] = cfg.value

        # Reports in headers are hidden by default in clang-tidy. Re-enable it
        # if the analyzer doesn't provide any other config options.
        if not analyzer_config:
            analyzer_config["HeaderFilterRegex"] = ".*"

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
            check_options = []

            for cfg in args.checker_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    check_options.append({
                        'key': f"{cfg.checker}.{cfg.option}",
                        'value': cfg.value})
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

        checkers = ClangTidy.get_analyzer_checkers()

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug_analyzer('No checkers were defined in '
                               'the command line for %s',
                               cls.ANALYZER_NAME)
            cmdline_checkers = []

        handler.initialize_checkers(
            checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        return handler
