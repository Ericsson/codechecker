# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Clang Static Analyzer related functions.
"""

import os
import plistlib
import re
import shlex
import subprocess

from typing import List

from codechecker_common.logger import get_logger

from codechecker_analyzer import analyzer_context, env
from codechecker_statistics_collector.collectors.special_return_value import \
    SpecialReturnValueCollector
from codechecker_statistics_collector.collectors.return_value import \
    ReturnValueCollector

from .. import analyzer_base
from ..config_handler import CheckerState
from ..flag import has_flag
from ..flag import prepend_all

from . import config_handler
from . import ctu_triple_arch
from . import version
from .ctu_autodetection import CTUAutodetection
from .result_handler import ClangSAResultHandler

LOG = get_logger('analyzer')


def parse_clang_help_page(
    command: List[str],
    start_label: str
) -> List[str]:
    """
    Parse the clang help page starting from a specific label.
    Returns a list of (flag, description) tuples.
    """
    try:
        help_page = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            env=analyzer_context.get_context().analyzer_env,
            universal_newlines=True,
            encoding="utf-8",
            errors="ignore")
    except (subprocess.CalledProcessError, OSError):
        LOG.debug("Failed to run '%s' command!", command)
        return []

    try:
        help_page = help_page[help_page.index(start_label) + len(start_label):]
    except ValueError:
        return []

    # This regex will match lines which contain only a flag or a flag and a
    # description: '  <flag>', '  <flag> <description>'.
    start_new_option_rgx = \
        re.compile(r"^\s{2}(?P<flag>\S+)(\s(?P<desc>[^\n]+))?$")

    # This regex will match lines which contain description for the previous
    # flag: '     <description>'
    prev_help_desc_rgx = \
        re.compile(r"^\s{3,}(?P<desc>[^\n]+)$")

    res = []

    flag = None
    desc = []
    for line in help_page.splitlines():
        m = start_new_option_rgx.match(line)
        if m:
            if flag and desc:
                res.append((flag, ' '.join(desc)))
                flag = None
                desc = []

            flag = m.group("flag")
        else:
            m = prev_help_desc_rgx.match(line)

        if m and m.group("desc"):
            desc.append(m.group("desc").strip())

    if flag and desc:
        res.append((flag, ' '.join(desc)))

    return res


def _is_user_disabled_checker(checker, ordered_checkers):
    """
    This function returns True if the given checker is disabled by the user
    explicitly by a --disable flag.
    """
    if not ordered_checkers:
        return False

    disabled_checkers = (c for c, enabled in ordered_checkers if not enabled)

    return any(checker.startswith(c) for c in disabled_checkers)


class ClangSA(analyzer_base.SourceAnalyzer):
    """
    Constructs clang static analyzer commands.
    """
    ANALYZER_NAME = 'clangsa'

    __ctu_autodetection = None

    def __init__(self, cfg_handler, buildaction):
        super().__init__(cfg_handler, buildaction)
        self.__disable_ctu = False
        self.__checker_configs = []
        self.__disabled_checkers = []

    @classmethod
    def analyzer_binary(cls):
        """
        Return the path of the analyzer binary.
        """
        return analyzer_context.get_context() \
            .analyzer_binaries[cls.ANALYZER_NAME]

    @classmethod
    def analyzer_plugins(cls) -> List[str]:
        """
        Return the list of .so file paths which contain checker plugins to
        ClangSA.
        """
        plugin_dir = analyzer_context.get_context().checker_plugin

        clangsa_plugin_dir = env.get_clangsa_plugin_dir()
        is_analyzer_from_path = env.is_analyzer_from_path()
        if is_analyzer_from_path:
            if not clangsa_plugin_dir:
                return []

            # If the CC_ANALYZERS_FROM_PATH and CC_CLANGSA_PLUGIN_DIR
            # environment variables are set we will use this value as the
            # plugin directory.
            plugin_dir = clangsa_plugin_dir

        if not plugin_dir or not os.path.exists(plugin_dir):
            return []

        return [os.path.join(plugin_dir, f)
                for f in os.listdir(plugin_dir)
                if os.path.isfile(os.path.join(plugin_dir, f))
                and f.endswith(".so")]

    @classmethod
    def __add_plugin_load_flags(cls, analyzer_cmd: List[str]):
        """
        ClangSA can be extended with checker plugins. This function extends a
        clang command with these plugins.
        """
        for plugin in ClangSA.analyzer_plugins():
            analyzer_cmd.extend(["-load", plugin])

    @classmethod
    def get_binary_version(cls, environ, details=False) -> str:
        # No need to LOG here, we will emit a warning later anyway.
        if not cls.analyzer_binary():
            return None

        if details:
            ver = [cls.analyzer_binary(), '--version']
        else:
            ver = [cls.analyzer_binary(), '-dumpversion']
        try:
            output = subprocess.check_output(ver,
                                             env=environ,
                                             universal_newlines=True,
                                             encoding="utf-8",
                                             errors="ignore")
            return output.strip()
        except (subprocess.CalledProcessError, OSError) as oerr:
            LOG.warning("Failed to get analyzer version: %s",
                        ' '.join(ver))
            LOG.warning(oerr)

        return None

    @classmethod
    def version_info(cls):
        return version.get(cls.analyzer_binary())

    @classmethod
    def ctu_capability(cls):
        """
        Return a CTUAutodetection object which describes the availability of
        CTU feature with some additional CTU-related info.
        """
        if not cls.__ctu_autodetection:
            cls.__ctu_autodetection = CTUAutodetection(
                cls.analyzer_binary(),
                analyzer_context.get_context().analyzer_env)

        return cls.__ctu_autodetection

    def is_ctu_available(self):
        """
        Check if ctu is available for the analyzer.
        If the ctu_dir is set in the config, the analyzer is capable to
        run ctu analysis.
        """
        return bool(self.config_handler.ctu_dir)

    def is_ctu_enabled(self):
        """
        Check if ctu is enabled for the analyzer.
        """
        return not self.__disable_ctu

    def disable_ctu(self):
        """
        Disable ctu even if ctu is available.
        By default it is enabled if available.
        """
        self.__disable_ctu = True

    def enable_ctu(self):
        self.__disable_ctu = False

    def add_checker_config(self, checker_cfg):
        """
        Add configuration options to specific checkers.
        checker_cfg should be a list of arguments in case of
        Clang Static Analyzer like this:
        ['-Xclang', '-analyzer-config', '-Xclang', 'checker_option=some_value']
        """

        self.__checker_configs.append(checker_cfg)

    @classmethod
    def get_analyzer_checkers(
        cls,
        alpha: bool = True,
        debug: bool = False
    ) -> List[str]:
        """
        Return the list of the supported checkers.

        Before clang9 alpha and debug checkers were printed by default. Since
        clang9 there are extra arguments to print the additional checkers.
        """
        command = [cls.analyzer_binary(), "-cc1"]

        cls.__add_plugin_load_flags(command)

        command.append("-analyzer-checker-help")

        # The clang compiler on OSX is a few
        # relases older than the open source clang release.
        # The new checker help printig flags are not available there yet.
        # If the OSX clang will be updated to based on clang v8
        # this early return can be removed.
        version_info = cls.version_info()
        if version_info and version_info.vendor == "clang":
            if alpha and version_info.major_version >= 9:
                command.append("-analyzer-checker-help-alpha")

            if debug and version_info.major_version >= 9:
                command.append("-analyzer-checker-help-developer")

        return parse_clang_help_page(command, 'CHECKERS:')

    @classmethod
    def get_checker_config(cls) -> List[str]:
        """
        Return the list of checker config options.

        Before clang9 alpha and debug checkers were printed by default. Since
        clang9 there are extra arguments to print the additional checkers.
        """
        command = [cls.analyzer_binary(), "-cc1"]

        cls.__add_plugin_load_flags(command)

        command.append("-analyzer-checker-option-help")

        version_info = ClangSA.version_info()
        if version_info.vendor == "clang":
            if version_info.major_version >= 9:
                command.append("-analyzer-checker-option-help-alpha")

            if version_info.major_version >= 9:
                command.append("-analyzer-checker-option-help-developer")

        return parse_clang_help_page(command, 'OPTIONS:')

    @classmethod
    def get_analyzer_config(cls) -> List[str]:
        """Return the list of analyzer config options."""
        command = [cls.analyzer_binary(), "-cc1"]

        cls.__add_plugin_load_flags(command)

        command.append("-analyzer-config-help")

        return parse_clang_help_page(command, 'OPTIONS:')

    def post_analyze(self, result_handler):
        """
        Disabled checkers are not actually disabled during analysis, because
        they might rely on each other under the hood. The disabled checkers'
        reports are removed in this post-processing step.
        """
        try:
            if not os.path.isfile(result_handler.analyzer_result_file):
                # This check has the same race-condition reason as the
                # exception, so see its description below.
                return

            with open(result_handler.analyzer_result_file, 'rb') as f:
                plist = plistlib.load(f)
        except plistlib.InvalidFileException:
            # It may happen that a compilation database contains a build action
            # multiple times (because it is compiled for several target
            # architectures), or at least they differ in a so minor part that
            # the same .plist file belongs to them. (For further details see
            # analyzer_action_str() in ResultHandler about the strange behavior
            # of make 4.3 in its -o flag.)
            # If this happens then the analysis of the same build action is
            # analyzed in parallel several times, so the same output .plist
            # file is changed by several threads. This may result an invalid
            # .plist which fails plistlib.load(). This is not a big problem,
            # because the second thread will also execute this post-processing
            # and it happens rarely anyways. test_compile_uniqueing() fails
            # undeterministically without this.
            return

        plist['diagnostics'] = list(filter(
            lambda diag: diag['check_name'] not in self.__disabled_checkers,
            plist.get('diagnostics', [])))

        with open(result_handler.analyzer_result_file, 'wb') as f:
            plistlib.dump(plist, f)

    def construct_analyzer_cmd(self, result_handler):
        """
        Called by the analyzer method.
        Construct the analyzer command.
        """
        try:
            # Get an output file from the result handler.
            analyzer_output_file = result_handler.analyzer_result_file

            # Get the checkers list from the config_handler.
            # Checker order matters.
            config = self.config_handler

            analyzer_cmd = [ClangSA.analyzer_binary(), '--analyze',
                            # Do not warn about the unused gcc/g++ arguments.
                            '-Qunused-arguments']

            for plugin in ClangSA.analyzer_plugins():
                analyzer_cmd.extend(["-Xclang", "-plugin",
                                     "-Xclang", "checkercfg",
                                     "-Xclang", "-load",
                                     "-Xclang", plugin])

            analyzer_mode = 'plist-multi-file'
            if config.analyze_headers:
                analyzer_cmd.extend(['-Xclang',
                                     '-analyzer-opt-analyze-headers'])

            analyzer_cmd.extend(['-Xclang',
                                 '-analyzer-output=' + analyzer_mode,
                                 '-o', analyzer_output_file])

            # Expand macros in plist output on the bug path.
            analyzer_cmd.extend(['-Xclang',
                                 '-analyzer-config',
                                 '-Xclang',
                                 'expand-macros=' +
                                 ('true' if config.expand_macros
                                  else 'false')])

            # Checker configuration arguments needs to be set before
            # the checkers.
            if self.__checker_configs:
                for cfg in self.__checker_configs:
                    analyzer_cmd.extend(cfg)

            # TODO: This object has a __checker_configs attribute and the
            # corresponding functions to set it. Either those should be used
            # for checker configs coming as command line argument, or those
            # should be eliminated.
            for cfg in config.checker_config:
                analyzer_cmd.extend(
                    ['-Xclang', '-analyzer-config', '-Xclang', cfg])

            # Config handler stores which checkers are enabled or disabled.
            self.__disabled_checkers = []
            enabled_checkers = []
            for checker_name, value in config.checks().items():
                state, _ = value
                if state == CheckerState.ENABLED:
                    enabled_checkers.append(checker_name)
                elif state == CheckerState.DISABLED:
                    self.__disabled_checkers.append(checker_name)

            if enabled_checkers:
                analyzer_cmd.extend(['-Xclang',
                                     '-analyzer-checker=' +
                                     ','.join(enabled_checkers)])
            # Enable aggressive-binary-operation-simplification option.
            version_info = ClangSA.version_info()
            if version_info and version_info.major_version >= 8:
                analyzer_cmd.extend([
                    '-Xclang',
                    '-analyzer-config',
                    '-Xclang',
                    'aggressive-binary-operation-simplification=true'])

            # Enable the z3 solver backend.
            if config.enable_z3:
                analyzer_cmd.extend(['-Xclang', '-analyzer-constraints=z3'])

            if config.enable_z3_refutation and not config.enable_z3:
                analyzer_cmd.extend(['-Xclang',
                                     '-analyzer-config',
                                     '-Xclang',
                                     'crosscheck-with-z3=true'])

            if config.ctu_dir and not self.__disable_ctu:
                analyzer_cmd.extend(
                    ['-Xclang', '-analyzer-config', '-Xclang',
                     'experimental-enable-naive-ctu-analysis=true',
                     '-Xclang', '-analyzer-config', '-Xclang',
                     'ctu-dir=' + self.get_ctu_dir()])
                ctu_display_progress = \
                    ClangSA.ctu_capability().display_progress
                if ctu_display_progress:
                    analyzer_cmd.extend(ctu_display_progress)

                if config.ctu_on_demand:
                    invocation_list_path = \
                        os.path.join(self.get_ctu_dir(), 'invocation-list.yml')
                    analyzer_cmd.extend(
                        ['-Xclang', '-analyzer-config', '-Xclang',
                         f'ctu-invocation-list={invocation_list_path}'
                         ])

            compile_lang = self.buildaction.lang
            if not has_flag('-x', analyzer_cmd):
                analyzer_cmd.extend(['-x', compile_lang])

            if not has_flag('--target', analyzer_cmd) and \
                    self.buildaction.target != "":
                analyzer_cmd.append(f"--target={self.buildaction.target}")

            if not has_flag('-arch', analyzer_cmd) and \
                    self.buildaction.arch != "":
                analyzer_cmd.extend(["-arch", self.buildaction.arch])

            if not has_flag('-std', analyzer_cmd) and \
                    self.buildaction.compiler_standard != "":
                analyzer_cmd.append(self.buildaction.compiler_standard)

            analyzer_cmd.extend(config.analyzer_extra_arguments)

            analyzer_cmd.extend(self.buildaction.analyzer_options)

            analyzer_cmd.extend(prepend_all(
                '-isystem',
                self.buildaction.compiler_includes))

            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    def get_ctu_dir(self):
        """
        Returns the path of the ctu directory (containing the triple).
        """
        config = self.config_handler
        triple_arch = ctu_triple_arch.get_triple_arch(self.buildaction,
                                                      self.source_file,
                                                      config)
        ctu_dir = os.path.join(config.ctu_dir, triple_arch)
        return ctu_dir

    def analyzer_mentioned_file_real_path(self, mentioned_path):
        """
        PCH-based an On-demand-parsed CTU modes use different paths and file
        suffixes. PCH-based mode uses ast dump files that are suffixed with
        '.ast', and they are supposed to be under the
        '<ctu-dir>/ast/<original-full-path>'. On-demand-parsed mode uses the
        full paths of the original source files.
        """
        pch_suffix = '.ast'

        # We convert the given file path to absolute path because we suppose
        # that in the clang's output the PCH files in CTU mode are relative
        # paths.
        mentioned_path = os.path.join(self.get_ctu_dir(), mentioned_path)

        # Detect the mode based on the path.
        suffix_index = mentioned_path.rfind(pch_suffix)
        # If the file does not have the suffix, the mode is On-demand-parsed.
        # Return the original path.
        if suffix_index == -1:
            LOG.debug("Analyzer mentioned path path: '%s', "
                      "corresponding source file: '%s'",
                      mentioned_path, mentioned_path)
            return mentioned_path

        # PCH-based mode stores files with their full path structure recreated
        # under <ctu-dir>/ast.
        ctu_ast_dir = os.path.join(self.get_ctu_dir(), 'ast')

        source_path = mentioned_path[len(ctu_ast_dir):suffix_index]

        LOG.debug("Analyzer mentioned path path: '%s', "
                  "corresponding source file: '%s'",
                  mentioned_path, source_path)

        if not mentioned_path.startswith(ctu_ast_dir):
            LOG.error(
                "Mentioned path '%s' ends with suffix '%s', but does "
                "not begin with supposed ast dir '%s'.", mentioned_path,
                pch_suffix, ctu_ast_dir)

        # Strip the prefix ast directory and the suffix.
        return mentioned_path[len(ctu_ast_dir):suffix_index]

    def get_analyzer_mentioned_files(self, output):
        """
        Parse ClangSA's output to generate a list of files that were mentioned
        in the standard output or standard error.
        """
        if not output:
            return set()

        regex_for_ctu_ast_load = re.compile(
            r"CTU loaded AST file: (.*)")

        paths = set()

        for line in output.splitlines():
            match = re.match(regex_for_ctu_ast_load, line)
            if match:
                path = match.group(1)
                paths.add(self.analyzer_mentioned_file_real_path(path))

        return paths

    @classmethod
    def resolve_missing_binary(cls, configured_binary, environ):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

        LOG.debug("%s not found in path for ClangSA!", configured_binary)

        if os.path.isabs(configured_binary):
            # Do not autoresolve if the path is an absolute path as there
            # is nothing we could auto-resolve that way.
            return False

        # clang, clang-5.0, clang++, clang++-5.1, ...
        clang = env.get_binary_in_path(['clang', 'clang++'],
                                       r'^clang(\+\+)?(-\d+(\.\d+){0,2})?$',
                                       environ)

        if clang:
            LOG.debug("Using '%s' for ClangSA!", clang)
        return clang

    @classmethod
    def is_binary_version_incompatible(cls, environ):
        """
        We support pretty much every ClangSA version.
        """
        return None

    def construct_result_handler(self, buildaction, report_output,
                                 skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = ClangSAResultHandler(buildaction, report_output,
                                           self.config_handler.report_hash)

        res_handler.skiplist_handler = skiplist_handler

        return res_handler

    @classmethod
    def construct_config_handler(cls, args):

        context = analyzer_context.get_context()
        environ = context.analyzer_env

        handler = config_handler.ClangSAConfigHandler(environ)

        handler.report_hash = args.report_hash \
            if 'report_hash' in args else None

        handler.enable_z3 = 'enable_z3' in args and args.enable_z3 == 'on'

        handler.enable_z3_refutation = 'enable_z3_refutation' in args and \
            args.enable_z3_refutation == 'on'

        handler.analyze_headers = 'analyze_headers' in args and \
                                  args.analyze_headers == 'on'

        handler.expand_macros = 'expand_macros' in args and \
                                args.expand_macros == 'on'

        if 'ctu_phases' in args:
            handler.ctu_dir = os.path.join(args.output_path,
                                           args.ctu_dir)
            handler.ctu_on_demand = \
                'ctu_ast_mode' in args and \
                args.ctu_ast_mode == 'parse-on-demand'

        try:
            with open(args.clangsa_args_cfg_file, 'r', encoding='utf8',
                      errors='ignore') as sa_cfg:
                handler.analyzer_extra_arguments = \
                    re.sub(r'\$\((.*?)\)',
                           env.replace_env_var(args.clangsa_args_cfg_file),
                           sa_cfg.read().strip())
                handler.analyzer_extra_arguments = \
                    shlex.split(handler.analyzer_extra_arguments)
        except IOError as ioerr:
            LOG.debug_analyzer(ioerr)
        except AttributeError as aerr:
            # No clangsa arguments file was given in the command line.
            LOG.debug_analyzer(aerr)

        checkers = ClangSA.get_analyzer_checkers()

        try:
            cmdline_checkers = args.ordered_checkers
        except AttributeError:
            LOG.debug_analyzer('No checkers were defined in '
                               'the command line for %s', cls.ANALYZER_NAME)
            cmdline_checkers = []

        handler.initialize_checkers(
            checkers,
            cmdline_checkers,
            'enable_all' in args and args.enable_all)

        # If --stats flag is provided then enable statistics-based checkers
        # unless explicitly disabled by the user.
        if 'stats_enabled' in args:
            # In some Clang versions, statisticsbased checkers are in the alpha
            # package (alpha.statisticsbased), and maybe not in others. Lets
            # figure out the actual checker name first.
            special_return_value = next((
                checker for checker, _ in checkers
                if SpecialReturnValueCollector.checker_analyze in checker),
                None)
            unchecked_return_value = next((
                checker for checker, _ in checkers
                if ReturnValueCollector.checker_analyze in checker),
                None)

            if special_return_value and not _is_user_disabled_checker(
                    special_return_value,
                    cmdline_checkers):
                handler.set_checker_enabled(special_return_value)

            if unchecked_return_value and not _is_user_disabled_checker(
                    unchecked_return_value,
                    cmdline_checkers):
                handler.set_checker_enabled(unchecked_return_value)

        # Statistics collector checkers must be explicitly disabled as they
        # trash the output. These checkers are executed in a preceding analysis
        # phase.
        handler.set_checker_enabled(
            SpecialReturnValueCollector.checker_collect, False)

        handler.set_checker_enabled(
            ReturnValueCollector.checker_collect, False)

        handler.checker_config = []

        # TODO: This extra "isinstance" check is needed for
        # CodeChecker checkers --checker-config. This command also runs
        # this function in order to construct a config handler.
        if 'checker_config' in args and isinstance(args.checker_config, list):
            for cfg in args.checker_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    handler.checker_config.append(
                        f"{cfg.checker}:{cfg.option}={cfg.value}")

        # TODO: This extra "isinstance" check is needed for
        # CodeChecker analyzers --analyzer-config. This command also runs
        # this function in order to construct a config handler.
        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    handler.checker_config.append(f"{cfg.option}={cfg.value}")

        return handler
