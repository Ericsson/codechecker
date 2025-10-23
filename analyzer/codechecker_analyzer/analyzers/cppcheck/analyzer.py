# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Cppcheck related functions.
"""

from collections import defaultdict
import sys
from typing import List
from packaging.version import Version
from pathlib import Path
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from codechecker_common.logger import get_logger
from codechecker_common import util

from codechecker_analyzer import analyzer_context
from codechecker_analyzer.env import get_binary_in_path

from .. import analyzer_base

from .config_handler import CppcheckConfigHandler
from .result_handler import CppcheckResultHandler

from ..config_handler import CheckerState

LOG = get_logger('analyzer.cppcheck')


def parse_checkers(cppcheck_output):
    """
    Parse cppcheck checkers list given by '--errorlist' flag. Return a list of
    (checker_name, description) pairs.
    """
    checkers = []

    tree = ET.ElementTree(ET.fromstring(cppcheck_output))
    root = tree.getroot()
    errors = root.find('errors')
    for error in errors.findall('error'):
        name = error.attrib.get('id')
        if name:
            name = "cppcheck-" + name
        msg = str(error.attrib.get('msg') or '')
        # TODO: Check severity handling in cppcheck
        # severity = error.attrib.get('severity')

        # checkers.append((name, msg, severity))
        checkers.append((name, msg))

    return checkers


def parse_version(cppcheck_output):
    """
    Parse cppcheck version output and return the version number.
    """
    version_re = re.compile(r'^Cppcheck(.*?)(?P<version>[\d\.]+)')
    match = version_re.match(cppcheck_output)
    if match:
        return match.group('version')
    return None


class Cppcheck(analyzer_base.SourceAnalyzer):
    """
    Constructs the Cppcheck analyzer commands.
    """

    ANALYZER_NAME = 'cppcheck'

    @classmethod
    def analyzer_binary(cls):
        return analyzer_context.get_context() \
            .analyzer_binaries[cls.ANALYZER_NAME]

    @classmethod
    def get_binary_version(cls, details=False) -> str:
        """ Get analyzer version information. """
        # No need to LOG here, we will emit a warning later anyway.
        if not cls.analyzer_binary():
            return None
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
        LOG.error("Checker configuration for Cppcheck is not implemented yet")

    def get_analyzer_mentioned_files(self, output):
        """
        Return a collection of files that were mentioned by the analyzer in
        its standard outputs, which should be analyzer_stdout or
        analyzer_stderr from a result handler.
        """

    def parse_analyzer_config(self):
        """
        Parses a set of a white listed compiler flags.
        Cppcheck can only use a subset of the parametes
        found in compilation commands.
        These are:
        * -I: flag for specifing include directories
        * -D: for build time defines
        * -U: for undefining names
        * -std: The languange standard
        Any other parameter different from the above list will be dropped.
        """
        params = []
        interesting_option = re.compile("-[IUD].*")
        # the std flag is different. the following are all valid flags:
        # * --std c99
        # * -std=c99
        # * --std=c99
        # BUT NOT:
        # * -std c99
        # * -stdlib=libc++
        std_regex = re.compile("-(-std$|-?std=.*)")

        # Mapping is needed, because, if a standard version not known by
        # cppcheck is used, then it will assume the latest available version
        # before cppcheck-2.15 or fail the analysis from cppcheck-2.15.
        # https://gcc.gnu.org/onlinedocs/gcc/C-Dialect-Options.html#index-std-1
        standard_mapping = {
            "c90": "c89",
            "c18": "c17",
            "iso9899:2017": "c17",
            "iso9899:2018": "c17",
            "iso9899:1990": "c89",
            "iso9899:199409": "c89",  # Good enough
            "c9x": "c99",
            "iso9899:1999": "c99",
            "iso9899:199x": "c99",
            "c1x": "c11",
            "iso9899:2011": "c11",
            "c2x": "c23",
            "iso9899:2024": "c23",
            "c++98": "c++03",
            "c++0x": "c++11",
            "c++1y": "c++14",
            "c++1z": "c++17",
            "c++2a": "c++20",
            "c++2b": "c++23",
            "c++2c": "c++26"
        }

        for i, analyzer_option in enumerate(self.buildaction.analyzer_options):
            if interesting_option.match(analyzer_option):
                params.extend([analyzer_option])
                # The above extend() won't properly insert the analyzer_option
                # in case of the following format -I <path/to/include>.
                # The below check will add the next item in the
                # analyzer_options list if the parameter is specified with a
                # space, as that should be actual path to the include.
                if interesting_option.match(analyzer_option).span() == (0, 2):
                    params.extend(
                        [self.buildaction.analyzer_options[i+1]]
                    )
            elif std_regex.match(analyzer_option):
                standard = ""
                if "=" in analyzer_option:
                    standard = analyzer_option.split("=")[-1]
                # Handle space separated parameter
                # The else clause is never executed until a log parser
                # limitation is addressed, as only this "-std=xxx" version
                # of the paramter is forwareded in the analyzer_option list.
                else:
                    standard = self.buildaction.analyzer_options[i+1]
                standard = standard.lower().replace("gnu", "c")
                standard = standard_mapping.get(standard, standard)
                params.extend(["--std=" + standard])
        return params

    def construct_analyzer_cmd(self, result_handler):
        """
        Construct analyzer command for cppcheck.
        """
        try:
            config = self.config_handler

            analyzer_cmd = [Cppcheck.analyzer_binary()]

            # TODO implement a more granular commandline checker config
            # Cppcheck runs with all checkers enabled for the time being
            # the unneded checkers are passed as suppressed checkers
            analyzer_cmd.append('--enable=all')

            for checker_name, value in config.checks().items():
                if value[0] == CheckerState.DISABLED:
                    # TODO python3.9 removeprefix method would be nicer
                    # than startswith and a hardcoded slicing
                    if checker_name.startswith("cppcheck-"):
                        checker_name = checker_name[9:]
                    analyzer_cmd.append('--suppress=' + checker_name)

            # unusedFunction check is for whole program analysis,
            # which is not compatible with per source file analysis.
            if '--suppress=unusedFunction' not in analyzer_cmd:
                analyzer_cmd.append('--suppress=unusedFunction')

            # Add extra arguments.
            analyzer_cmd.extend(config.analyzer_extra_arguments)

            # Pass whitelisted parameters
            params = self.parse_analyzer_config()

            def is_std(arg):
                return arg.startswith("--std=")

            if util.index_of(config.analyzer_extra_arguments, is_std) >= 0:
                std_idx = util.index_of(params, is_std)
                if std_idx >= 0:
                    del params[std_idx]

            analyzer_cmd.extend(params)

            # TODO fix this in a follow up patch, because it is failing
            # the macos pypy test.
            # analyzer_cmd.extend(["--std=" +
            #                    self.buildaction.compiler_standard
            #                    .split("=")[-1].lower().replace("gnu", "c")])

            # By default there is no platform configuration,
            # but a platform definition xml can be specified.
            if 'platform' in config.analyzer_config:
                analyzer_cmd.append(
                        "--platform=" + config.analyzer_config['platform'][0])
            else:
                analyzer_cmd.append("--platform=native")

            if 'inconclusive' in config.analyzer_config:
                analyzer_cmd.append("--inconclusive")

            if 'addons' in config.analyzer_config:
                analyzer_cmd.extend(
                    f"--addon={addon}" for addon
                    in config.analyzer_config["addons"])

            if 'libraries' in config.analyzer_config:
                analyzer_cmd.extend(
                    f"--library={library}" for library
                    in config.analyzer_config["libraries"])

            # TODO Suggest a better place for this
            # cppcheck wont create the output folders for itself
            output_dir = Path(result_handler.workspace, "cppcheck",
                              result_handler.buildaction_hash)
            output_dir.mkdir(exist_ok=True)

            analyzer_cmd.append('--plist-output=' + str(output_dir))

            analyzer_cmd.append(self.source_file)

            return analyzer_cmd

        except Exception as ex:
            LOG.error(ex)
            return []

    @classmethod
    def get_analyzer_checkers(cls):
        """
        Return the list of the supported checkers.
        """
        if not cls.analyzer_binary():
            return []
        command = [cls.analyzer_binary(), "--errorlist"]
        environ = analyzer_context.get_context().get_env_for_bin(
            command[0])
        try:
            errorlist_output = subprocess.check_output(command, env=environ)
            checkers = parse_checkers(errorlist_output)

            # Cppcheck can and will report with checks that have a different
            # name than marked in the --errorlist xml. To be able to suppress
            # these reports, the checkerlist needs to be extended by those
            # found in the label file.
            checkers_from_label = analyzer_context \
                .get_context().checker_labels.checkers("cppcheck")
            parsed_checker_names = set(checker[0] for checker in checkers)
            for checker in set(checkers_from_label):
                if checker not in parsed_checker_names:
                    checkers.append((checker, ""))

            return checkers
        except (subprocess.CalledProcessError) as e:
            LOG.error(e.stderr)
        except (OSError) as e:
            LOG.error(e.errno)
        return []

    @classmethod
    def get_analyzer_config(cls) -> List[analyzer_base.AnalyzerConfig]:
        """
        Config options for cppcheck.
        """
        return [
            analyzer_base.AnalyzerConfig(
                "addons",
                "A list of cppcheck addon files.",
                str),
            analyzer_base.AnalyzerConfig(
                "libraries",
                "A list of cppcheck library definiton files.",
                str),
            analyzer_base.AnalyzerConfig(
                "platform",
                "The platform configuration .xml file.",
                str),
            analyzer_base.AnalyzerConfig(
                "inconclusive",
                "Enable inconclusive reports.",
                str),
            analyzer_base.AnalyzerConfig(
                "cc-verbatim-args-file",
                "A file path containing flags that are forwarded verbatim to "
                "the analyzer tool. E.g.: cc-verbatim-args-file=<filepath>",
                util.ExistingPath)
        ]

    def post_analyze(self, result_handler):
        """
        Post process the reuslts after the analysis.
        Will copy the plist files created by cppcheck into the
        root of the reports folder.
        Renames the source plist files to *.plist.bak because
        The report parsing of the Parse command is done recursively.

        """
        # Cppcheck can generate an id into the output plist file name
        # we get "the" *.plist file from the unique output folder

        cppcheck_out_folder = Path(result_handler.workspace,
                                   "cppcheck",
                                   result_handler.buildaction_hash)
        cppcheck_outs = cppcheck_out_folder.glob('**/*.plist')

        for cppcheck_out in list(cppcheck_outs):
            codechecker_out = os.path.join(result_handler.workspace,
                                           result_handler.analyzer_result_file)

            # plists generated by cppcheck are still "parsable" by our plist
            # parser. Renaming is needed to circumvent the processing of the
            # raw files.
            try:
                shutil.copy2(cppcheck_out, codechecker_out)
                Path(cppcheck_out).rename(str(cppcheck_out) + ".bak")
            except (OSError) as e:
                LOG.error(e.errno)

    @classmethod
    def resolve_missing_binary(cls, configured_binary, environ):
        """
        In case of the configured binary for the analyzer is not found in the
        PATH, this method is used to find a callable binary.
        """

        LOG.debug("%s not found in path for Cppcheck!", configured_binary)

        if os.path.isabs(configured_binary):
            # Do not autoresolve if the path is an absolute path as there
            # is nothing we could auto-resolve that way.
            return False

        cppcheck = get_binary_in_path(['cppcheck'],
                                      r'^cppcheck(-\d+(\.\d+){0,2})?$',
                                      environ)

        if cppcheck:
            LOG.debug("Using '%s' for Cppcheck!", cppcheck)
        return cppcheck

    @classmethod
    def is_binary_version_incompatible(cls):
        """
        Check the version compatibility of the given analyzer binary.
        """
        analyzer_version = cls.get_binary_version()

        # The analyzer version should be above 1.80 because '--plist-output'
        # argument was introduced in this release.
        if Version(analyzer_version) >= Version("1.80"):
            return None

        return "CppCheck binary found is too old at " \
               f"v{str(analyzer_version).strip()}; minimum version is 1.80"

    def construct_result_handler(self, buildaction, report_output,
                                 skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = CppcheckResultHandler(buildaction, report_output,
                                            self.config_handler.report_hash)

        res_handler.skiplist_handler = skiplist_handler
        res_handler.analyzer = self

        return res_handler

    @classmethod
    def construct_config_handler(cls, args):
        handler = CppcheckConfigHandler()

        analyzer_config = defaultdict(list)

        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                if cfg.analyzer == cls.ANALYZER_NAME:
                    analyzer_config[cfg.option].append(cfg.value)

        handler.analyzer_config = analyzer_config

        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            for cfg in args.analyzer_config:
                if cfg.analyzer == cls.ANALYZER_NAME and \
                        cfg.option == 'cc-verbatim-args-file':
                    try:
                        handler.analyzer_extra_arguments = \
                            util.load_args_from_file(cfg.value)
                    except FileNotFoundError:
                        LOG.error(f"File not found: {cfg.value}")
                        sys.exit(1)

        checkers = cls.get_analyzer_checkers()

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
