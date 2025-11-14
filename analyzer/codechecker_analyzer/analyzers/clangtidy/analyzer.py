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
from pathlib import Path
import re
from semver.version import Version
import shutil
import subprocess
import sys
from typing import Iterable, List, Optional, Set, Tuple

import yaml

from codechecker_common import util
from codechecker_common.logger import get_logger

from codechecker_analyzer import analyzer_context, env

from .. import analyzer_base
from ..config_handler import CheckerState
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
    clang_tidy_bin = context.analyzer_binaries.get(ClangTidy.ANALYZER_NAME)

    if not clang_tidy_bin:
        return None

    path_env = os.environ.get('PATH', '').split(os.pathsep)
    clang_tidy_path = Path(clang_tidy_bin)

    if clang_tidy_path.resolve().name == 'ccache':
        for i, path in enumerate(path_env):
            if Path(path) == clang_tidy_path.parent:
                pos = i
                break

        clang_tidy_bin = shutil.which(
            clang_tidy_path.name,
            path=os.pathsep.join(path_env[pos + 1:]))

        if not clang_tidy_bin:
            return None

    # Resolve symlink.
    clang_tidy_bin = Path(clang_tidy_bin).resolve()

    # Find diagtool next to the clang binary.
    diagtool_bin = clang_tidy_bin.parent / 'diagtool'
    if diagtool_bin.exists():
        return diagtool_bin

    # Sometimes diagtool binary has a version number in its name: diagtool-14.
    version = ClangTidy.get_binary_version()

    if version and \
            diagtool_bin.with_name(f'diagtool-{version.major}').exists():
        return diagtool_bin

    LOG.warning(
        "'diagtool' can not be found next to the clang binary (%s)!",
        clang_tidy_bin)

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


class ClangTidy(analyzer_base.SourceAnalyzer):
    """
    Constructs the clang tidy analyzer commands.
    """

    ANALYZER_NAME = 'clang-tidy'

    # Cache object for get_analyzer_checkers().
    __analyzer_checkers = None

    __additional_analyzer_config = [
        analyzer_base.AnalyzerConfig(
            'cc-verbatim-args-file',
            'A file path containing flags that are forwarded verbatim to the '
            'analyzer tool. E.g.: cc-verbatim-args-file=<filepath>',
            util.ExistingPath),
        analyzer_base.AnalyzerConfig(
            'take-config-from-directory',
            'The .clang-tidy config file should be taken into account when '
            'analysis is executed through CodeChecker. Possible values: true, '
            'false. Default: false',
            str)
    ]

    @classmethod
    def analyzer_binary(cls):
        return analyzer_context.get_context() \
            .analyzer_binaries[cls.ANALYZER_NAME]

    @classmethod
    def get_binary_version(cls) -> Optional[Version]:
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
            version_re = re.compile(r'.*version (?P<version>[\d\.]+)', re.S)
            match = version_re.match(output)
            if match:
                return Version.parse(match.group('version'))
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

            context = analyzer_context.get_context()

            blacklisted_checkers = context.checker_labels.checkers_by_labels(
                ["blacklist:true"], cls.ANALYZER_NAME)

            environ = context.get_env_for_bin(cls.analyzer_binary())
            result = subprocess.check_output(
                [cls.analyzer_binary(), "-list-checks", "-checks=*"],
                env=environ,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
            checker_description = parse_checkers(result)

            checker_description.extend(
                (checker, "")
                for checker in map(lambda x: f"clang-diagnostic-{x}",
                                   get_warnings())
                if checker not in blacklisted_checkers)

            checker_description.append(("clang-diagnostic-error",
                                        "Indicates compiler errors."))

            cls.__analyzer_checkers = checker_description

            return checker_description
        except (subprocess.CalledProcessError, OSError):
            return []

    @classmethod
    def get_checker_config(cls) -> List[analyzer_base.CheckerConfig]:
        """
        Return the checker configuration of the all of the supported checkers.
        """
        try:
            help_page = subprocess.check_output(
                [cls.analyzer_binary(), "-dump-config", "-checks=*"],
                env=analyzer_context.get_context()
                .get_env_for_bin(cls.analyzer_binary()),
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore")
        except (subprocess.CalledProcessError, OSError):
            return []

        result = []
        for cfg, doc in parse_checker_config(help_page):
            result.append(analyzer_base.CheckerConfig(*cfg.split(':', 1), doc))

        return result

    @classmethod
    def get_analyzer_config(cls) -> List[analyzer_base.AnalyzerConfig]:
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
            native_config = parse_analyzer_config(result)
        except (subprocess.CalledProcessError, OSError):
            native_config = []

        native_config = map(
            lambda cfg: analyzer_base.AnalyzerConfig(cfg[0], cfg[1], str),
            native_config)

        return list(native_config) + list(cls.__additional_analyzer_config)

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

        CLANG_DIAGNOSTIC_PREFIX = 'clang-diagnostic-'

        # Config handler stores which checkers are enabled or disabled.
        for checker_name, value in config.checks().items():
            state, _ = value

            if checker_name.startswith(CLANG_DIAGNOSTIC_PREFIX):
                # If a clang-diagnostic-... is enabled add it as a compiler
                # warning as -W..., if it is disabled, tidy can suppress when
                # specified in the -checks parameter list, so we add it there
                # as -clang-diagnostic-... .

                # TODO: str.removeprefix() available in Python 3.9
                warning_name = checker_name[len(CLANG_DIAGNOSTIC_PREFIX):]

                if state == CheckerState.ENABLED:
                    if checker_name == 'clang-diagnostic-error':
                        # Disable warning of clang-diagnostic-error to
                        # avoid generated compiler errors.
                        compiler_warnings.append('-Wno-' + warning_name)
                    else:
                        compiler_warnings.append('-W' + warning_name)
                else:
                    compiler_warnings.append('-Wno-' + warning_name)

            if state == CheckerState.ENABLED:
                enabled_checkers.append(checker_name)

        # By default all checkers are disabled and the enabled ones
        # are added explicitly.
        checkers = ['-*']

        # If only clang-diagnostic-* checkers are enabled,
        # we need to add a dummy checker otherwise clang-tidy
        # will fail with the following error: "no checks enabled"
        if all(c.startswith(CLANG_DIAGNOSTIC_PREFIX) for c
            in enabled_checkers):
            dummy_checker_name = "darwin-dispatch-once-nonstatic"
            checkers.append(dummy_checker_name)

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

        analyzer_config = {}
        # TODO: This extra "isinstance" check is needed for
        # CodeChecker analyzers --analyzer-config. This command also
        # runs this function in order to construct a config handler.
        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                # TODO: The analyzer plugin should get only its own analyzer
                # config options from outside.
                if cfg.analyzer != cls.ANALYZER_NAME:
                    continue

                if cfg.option == 'cc-verbatim-args-file':
                    try:
                        handler.analyzer_extra_arguments = \
                            util.load_args_from_file(cfg.value)
                    except FileNotFoundError:
                        LOG.error(f"File not found: {cfg.value}")
                        sys.exit(1)
                else:
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
                LOG.debug(ioerr)
            except AttributeError as aerr:
                # No clang tidy config file was given in the command line.
                LOG.debug(aerr)

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
            LOG.debug('No checkers were defined in the command line for %s',
                      cls.ANALYZER_NAME)
            cmdline_checkers = []

        handler.initialize_checkers(
            checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        return handler
