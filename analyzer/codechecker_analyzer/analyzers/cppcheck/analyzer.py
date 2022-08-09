# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""
from distutils.version import StrictVersion
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import xml.etree.ElementTree as ET

from codechecker_common.logger import get_logger

from codechecker_analyzer.env import extend, get_binary_in_path, \
    replace_env_var

from .. import analyzer_base

from .config_handler import CppcheckConfigHandler
from .result_handler import CppcheckResultHandler

from ..config_handler import CheckerState

LOG = get_logger('analyzer.cppcheck')


def parse_checkers(cppcheck_output):
    """
    Parse cppcheck checkers list.
    """
    checkers = []

    tree = ET.ElementTree(ET.fromstring(cppcheck_output))
    root = tree.getroot()
    errors = root.find('errors')
    for error in errors.findall('error'):
        name = error.attrib.get('id')
        if name:
            name = "cppcheck-" + name
        msg = error.attrib.get('msg')
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

    return None


class Cppcheck(analyzer_base.SourceAnalyzer):
    """
    Constructs the clang tidy analyzer commands.
    """

    ANALYZER_NAME = 'cppcheck'

    def add_checker_config(self, checker_cfg):
        LOG.error("Not implemented yet")

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

            # Enable or disable checkers.
            enabled_severity_levels = set()

            # Cppcheck runs with all checkers enabled for the time being
            # the unneded checkers are passed as suppressed checkers
            analyzer_cmd.append('--enable=all')

            if enabled_severity_levels:
                analyzer_cmd.append('--enable=' +
                                    ','.join(enabled_severity_levels))

            for checker_name, value in config.checks().items():
                if value[0] == CheckerState.disabled:
                    if checker_name.startswith("cppcheck-"):
                        checker_name = checker_name[9:]
                    # TODO python3.9 removeprefix method is better than lstrip
                    analyzer_cmd.append('--suppress=' + checker_name)

            # unusedFunction check is for whole program analysis, which is not compatible with
            # per source file analysis.
            analyzer_cmd.append('--suppress=unusedFunction')

            # Add extra arguments.
            analyzer_cmd.extend(config.analyzer_extra_arguments)

            # Add includes.
            for analyzer_option in self.buildaction.analyzer_options:
                if analyzer_option.startswith("-I") or \
                    analyzer_option.startswith("-D"):
                    analyzer_cmd.extend([analyzer_option])
                elif analyzer_option.startswith("-std"):
                    standard = analyzer_option.split("=")[-1] \
                        .lower().replace("gnu", "c")
                    analyzer_cmd.extend(["--std=" + standard])

            # By default there is no platform configuration, but a platform definition xml can be specified.
            if 'platform' in config.analyzer_config:
                analyzer_cmd.append("--platform=" + config.analyzer_config['platform'][0])
            else:
                analyzer_cmd.append("--platform=native")

            if 'addons' in config.analyzer_config:
                for addon in config.analyzer_config["addons"]:
                    analyzer_cmd.extend(["--addon=" + str(Path(addon).absolute())])
                #addons = " ".join(config.analyzer_config["cppcheck-addons"])
                #analyzer_cmd.extend(["--addon=" + addons])

            if 'libraries' in config.analyzer_config:
                for lib in config.analyzer_config["libraries"]:
                    analyzer_cmd.extend(["--library=" + str(Path(lib).absolute())])

            # Cppcheck does not handle compiler includes well
            #for include in self.buildaction.compiler_includes:
            #    analyzer_cmd.extend(['-I',  include])

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
            command = shlex.split(' '.join(command))
            result = subprocess.check_output(command, env=env)
            return parse_checkers(result)
        except (subprocess.CalledProcessError, OSError):
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
        Copies the generated plist file with a unique name,

        """
        file_name = os.path.splitext(os.path.basename(self.source_file))[0]
        cppcheck_out = os.path.join(result_handler.workspace, "cppcheck",
                                    result_handler.buildaction_hash,
                                   file_name + '.plist')
        if os.path.exists(cppcheck_out):
            codechecker_out = os.path.join(result_handler.workspace,
                                  result_handler.analyzer_result_file)

            shutil.copy2(cppcheck_out, codechecker_out)
            Path(cppcheck_out).rename(cppcheck_out + ".bak")

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
        Checker the version compatibility of the given analyzer binary.
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
        # cppcheck_bin = cls.resolve_missing_binary('cppcheck', check_env)

        # handler.compiler_resource_dir = \
        #    host_check.get_resource_dir(cppcheck_bin, context)

        checkers = cls.get_analyzer_checkers(handler, check_env)

        # TODO implement this / Read cppcheck checkers from the label file.
        # cppcheck_checkers = context.checker_labels.get(cls.ANALYZER_NAME +
        #                                               '_checkers')

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
