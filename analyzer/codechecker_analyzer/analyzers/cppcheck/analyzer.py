# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
"""
from distutils.version import StrictVersion
import os
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET

from codechecker_common.logger import get_logger

from codechecker_analyzer.env import extend, get_binary_in_path, \
    replace_env_var

from .. import analyzer_base

from .config_handler import CppcheckConfigHandler
from .result_handler import CppcheckResultHandler

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
            suppressed_checkers = set()
            for checker_name, value in config.checks().items():
                if not value[0]:
                    suppressed_checkers.add(checker_name)
                # TODO: Check severity handling in cppcheck
                # elif value.severity and value.severity != 'error':
                #    enabled_severity_levels.add(value.severity)

            if enabled_severity_levels:
                analyzer_cmd.append('--enable=' +
                                    ','.join(enabled_severity_levels))

            for checker_name in suppressed_checkers:
                analyzer_cmd.append('--suppress=' + checker_name)

            # Add extra arguments.
            analyzer_cmd.extend(config.analyzer_extra_arguments)

            # Add includes.
            for analyzer_option in self.buildaction.analyzer_options:
                if analyzer_option.startswith("-I") or \
                    analyzer_option.startswith("-D"):
                    analyzer_cmd.extend([analyzer_option])

            # Cppcheck does not handle compiler includes well
            #for include in self.buildaction.compiler_includes:
            #    print(include)
            #    analyzer_cmd.extend(['-I',  include])

            analyzer_cmd.append('--plist-output=' + result_handler.workspace)
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
        TODO add config options for cppcheck.
        """
        return []

    @classmethod
    def get_checker_config(cls, cfg_handler, environ):
        """
        TODO add config options for cppcheck checkers.
        """
        return []

    def post_analyze(self, result_handler):
        """
        Renames the generated plist file with a unique name.
        """
        file_name = os.path.splitext(os.path.basename(self.source_file))[0]
        output_file = os.path.join(result_handler.workspace,
                                   file_name + '.plist')
        if os.path.exists(output_file):
            output = os.path.join(result_handler.workspace,
                                  result_handler.analyzer_result_file)

            os.rename(output_file, output)

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

        check_env = extend(context.path_env_extra,
                           context.ld_lib_path_extra)

        # Overwrite PATH to contain only the parent of the cppcheck binary.
        if os.path.isabs(handler.analyzer_binary):
            check_env['PATH'] = os.path.dirname(handler.analyzer_binary)
        # cppcheck_bin = cls.resolve_missing_binary('cppcheck', check_env)

        # handler.compiler_resource_dir = \
        #    host_check.get_resource_dir(cppcheck_bin, context)

        try:
            with open(args.cppcheck_args_cfg_file, 'rb') as cppcheck_cfg:
                handler.analyzer_extra_arguments = \
                    re.sub(r'\$\((.*?)\)', replace_env_var,
                           cppcheck_cfg.read().strip())
                handler.analyzer_extra_arguments = \
                    shlex.split(handler.analyzer_extra_arguments)
        except IOError as ioerr:
            LOG.debug_analyzer(ioerr)
        except AttributeError as aerr:
            # No Cppcheck arguments file was given in the command line.
            LOG.debug_analyzer(aerr)

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
