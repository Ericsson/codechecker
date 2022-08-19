# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
"""
# TODO distutils will be removed in python3.12
from distutils.version import StrictVersion
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import xml.etree.ElementTree as ET

from codechecker_common.logger import get_logger

from codechecker_analyzer.env import extend, get_binary_in_path

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
    version_re = re.compile(r'^Cppcheck (?P<version>[\d\.]+)')
    match = version_re.match(cppcheck_output)
    if match:
        return StrictVersion(match.group('version'))


class Cppcheck(analyzer_base.SourceAnalyzer):
    """
    Constructs the Cppcheck analyzer commands.
    """

    ANALYZER_NAME = 'cppcheck'

    def add_checker_config(self, checker_cfg):
        LOG.error("Checker configuration for Cppcheck is not implemented yet")

    def get_analyzer_mentioned_files(self, output):
        """
        Return a collection of files that were mentioned by the analyzer in
        its standard outputs, which should be analyzer_stdout or
        analyzer_stderr from a result handler.
        """
        pass

    def construct_analyzer_cmd(self, result_handler):
        """
        Construct analyzer command for cppcheck.
        """
        try:
            config = self.config_handler

            analyzer_cmd = [config.analyzer_binary]

            # TODO implement a more granular commandline checker config
            # Cppcheck runs with all checkers enabled for the time being
            # the unneded checkers are passed as suppressed checkers
            analyzer_cmd.append('--enable=all')

            for checker_name, value in config.checks().items():
                if value[0] == CheckerState.disabled:
                    # TODO python3.9 removeprefix method would be nicer
                    # than startswith and a hardcoded slicing
                    if checker_name.startswith("cppcheck-"):
                        checker_name = checker_name[9:]
                    analyzer_cmd.append('--suppress=' + checker_name)

            # unusedFunction check is for whole program analysis,
            # which is not compatible with per source file analysis.
            analyzer_cmd.append('--suppress=unusedFunction')

            # Add extra arguments.
            analyzer_cmd.extend(config.analyzer_extra_arguments)

            # Pass includes, and macro (un)definitions
            for analyzer_option in self.buildaction.analyzer_options:
                if analyzer_option.startswith("-I") or \
                        analyzer_option.startswith("-U") or \
                        analyzer_option.startswith("-D"):
                    analyzer_cmd.extend([analyzer_option])
                elif analyzer_option.startswith("-i"):
                    analyzer_cmd.extend(["-I" + analyzer_option[2:]])
                elif analyzer_option.startswith("-std"):
                    standard = analyzer_option.split("=")[-1] \
                        .lower().replace("gnu", "c")
                    analyzer_cmd.extend(["--std=" + standard])

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

            if 'addons' in config.analyzer_config:
                for addon in config.analyzer_config["addons"]:
                    analyzer_cmd.extend(
                            ["--addon=" + str(Path(addon).absolute())])

            if 'libraries' in config.analyzer_config:
                for lib in config.analyzer_config["libraries"]:
                    analyzer_cmd.extend(
                            ["--library=" + str(Path(lib).absolute())])

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
    def get_analyzer_checkers(
            cls,
            cfg_handler: CppcheckConfigHandler,
            env):
        """
        Return the list of the supported checkers.
        """
        command = [cfg_handler.analyzer_binary, "--errorlist"]

        try:
            result = subprocess.check_output(command, env=env)
            return parse_checkers(result)
        except (subprocess.CalledProcessError) as e:
            LOG.error(e.stderr)
        except (OSError) as e:
            LOG.error(e.errno)
        return []

    @classmethod
    def get_analyzer_config(cls, cfg_handler, environ):
        """
        Config options for cppcheck.
        """
        return [("addons", "A list of cppcheck addon files."),
                ("libraries", "A list of cppcheck library definiton files."),
                ("platform", "The platform configuration .xml file.")
                ]

    @classmethod
    def get_checker_config(cls, cfg_handler, environ):
        """
        TODO add config options for cppcheck checkers.
        """
        return []

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
            except(OSError) as e:
                LOG.error(e.errno)

    @classmethod
    def resolve_missing_binary(cls, configured_binary, env):
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
                                      env)

        if cppcheck:
            LOG.debug("Using '%s' for Cppcheck!", cppcheck)
        return cppcheck

    @classmethod
    def __get_analyzer_version(cls, analyzer_binary, env):
        """
        Return the analyzer version.
        """
        command = [analyzer_binary, "--version"]

        try:
            command = shlex.split(' '.join(command))
            result = subprocess.check_output(
                    command,
                    env=env,
                    encoding="utf-8",
                    errors="ignore")
            return parse_version(result)
        except (subprocess.CalledProcessError, OSError):
            return []

    @classmethod
    def version_compatible(cls, configured_binary, environ):
        """
        Check the version compatibility of the given analyzer binary.
        """
        analyzer_version = \
            cls.__get_analyzer_version(configured_binary, environ)

        # The analyzer version should be above 1.80 because '--plist-output'
        # argument was introduced in this release.
        if analyzer_version >= StrictVersion("1.80"):
            return True

        return False

    def construct_result_handler(self, buildaction, report_output,
                                 checker_labels, skiplist_handler):
        """
        See base class for docs.
        """
        res_handler = CppcheckResultHandler(buildaction, report_output,
                                            self.config_handler.report_hash)

        res_handler.checker_labels = checker_labels
        res_handler.skiplist_handler = skiplist_handler

        return res_handler

    @classmethod
    def construct_config_handler(cls, args, context):
        handler = CppcheckConfigHandler()
        handler.analyzer_binary = context.analyzer_binaries.get(
            cls.ANALYZER_NAME)

        analyzer_config = {}

        if 'analyzer_config' in args and \
                isinstance(args.analyzer_config, list):
            r = re.compile(r'(?P<analyzer>.+?):(?P<key>.+?)=(?P<value>.+)')
            for cfg in args.analyzer_config:
                m = re.search(r, cfg)
                if m.group('analyzer') == cls.ANALYZER_NAME:
                    key = m.group('key')
                    if key not in analyzer_config:
                        analyzer_config[key] = []
                    analyzer_config[m.group('key')].append(m.group('value'))

        handler.analyzer_config = analyzer_config

        check_env = extend(context.path_env_extra,
                           context.ld_lib_path_extra)

        # Overwrite PATH to contain only the parent of the cppcheck binary.
        if os.path.isabs(handler.analyzer_binary):
            check_env['PATH'] = os.path.dirname(handler.analyzer_binary)

        checkers = cls.get_analyzer_checkers(handler, check_env)

        # Cppcheck can and will report with checks that have a different
        # name than marked in the --errorlist xml. To be able to suppress
        # these reports, the checkerlist needs to be extended by those found
        # in the label file.
        checker_labels = context.checker_labels
        checkers_from_label = checker_labels.checkers("cppcheck")
        parsed_set = set([data[0] for data in checkers])
        for checker in set(checkers_from_label):
            if checker not in parsed_set:
                checkers.append((checker, ""))

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
