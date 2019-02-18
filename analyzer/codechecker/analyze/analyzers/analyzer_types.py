# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Supported analyzer types.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import re
import subprocess

from libcodechecker.env import get_check_env
from libcodechecker.logger import get_logger

from .. import host_check

from .analyzer_clang_tidy import ClangTidy
from .analyzer_clangsa import ClangSA

LOG = get_logger('analyzer')

supported_analyzers = {ClangSA.ANALYZER_NAME: ClangSA,
                       ClangTidy.ANALYZER_NAME: ClangTidy}


def is_ctu_capable(context):
    """ Detects if the current clang is CTU compatible. """
    ctu_func_map_cmd = context.ctu_func_map_cmd
    try:
        version = subprocess.check_output([ctu_func_map_cmd, '-version'])
    except (subprocess.CalledProcessError, OSError):
        version = 'ERROR'
    return version != 'ERROR'


def is_statistics_capable(context):
    """ Detects if the current clang is Statistics compatible. """
    # Resolve potentially missing binaries.
    check_supported_analyzers([ClangSA.ANALYZER_NAME], context)
    clangsa_cfg = ClangSA.construct_config_handler([], context)

    check_env = get_check_env(context.path_env_extra,
                              context.ld_lib_path_extra)

    checkers = ClangSA.get_analyzer_checkers(clangsa_cfg, check_env)

    stat_checkers_pattern = re.compile(r'.+statisticscollector.+')

    for checker_name, _ in checkers:
        if stat_checkers_pattern.match(checker_name):
            return True

    return False


def check_supported_analyzers(analyzers, context):
    """
    Checks the given analyzers in the current context for their executability
    and support in CodeChecker.

    This method also updates the given context.analyzer_binaries if the
    context's configuration is bogus but had been resolved.

    :return: (enabled, failed) where enabled is a list of analyzer names
     and failed is a list of (analyzer, reason) tuple.
    """

    check_env = get_check_env(context.path_env_extra,
                              context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = set()
    failed_analyzers = set()

    for analyzer_name in analyzers:
        if analyzer_name not in supported_analyzers:
            failed_analyzers.add((analyzer_name,
                                  "Analyzer unsupported by CodeChecker."))
            continue

        # Get the compiler binary to check if it can run.
        available_analyzer = True
        analyzer_bin = analyzer_binaries.get(analyzer_name)
        if not analyzer_bin:
            failed_analyzers.add((analyzer_name,
                                  "Failed to detect analyzer binary."))
            available_analyzer = False
        elif not os.path.isabs(analyzer_bin):
            # If the analyzer is not in an absolute path, try to find it...
            found_bin = supported_analyzers[analyzer_name].\
                resolve_missing_binary(analyzer_bin, check_env)

            # found_bin is an absolute path, an executable in one of the
            # PATH folders.
            # If found_bin is the same as the original binary, ie., normally
            # calling the binary without any search would have resulted in
            # the same binary being called, it's NOT a "not found".
            if found_bin and os.path.basename(found_bin) != analyzer_bin:
                LOG.debug("Configured binary '%s' for analyzer '%s' was "
                          "not found, but environment PATH contains '%s'.",
                          analyzer_bin, analyzer_name, found_bin)
                context.analyzer_binaries[analyzer_name] = found_bin

            analyzer_bin = found_bin

        if not analyzer_bin or \
           not host_check.check_clang(analyzer_bin, check_env):
            # Analyzers unavailable under absolute paths are deliberately a
            # configuration problem.
            failed_analyzers.add((analyzer_name,
                                  "Cannot execute analyzer binary."))
            available_analyzer = False

        if available_analyzer:
            enabled_analyzers.add(analyzer_name)

    return enabled_analyzers, failed_analyzers


def construct_analyzer(buildaction,
                       analyzer_config_map):
    try:
        analyzer_type = buildaction.analyzer_type
        # Get the proper config handler for this analyzer type.
        config_handler = analyzer_config_map.get(analyzer_type)

        LOG.debug_analyzer('Constructing %s analyzer.', analyzer_type)
        if analyzer_type in supported_analyzers:
            analyzer = supported_analyzers[analyzer_type](config_handler,
                                                          buildaction)
        else:
            analyzer = None
            LOG.error('Unsupported analyzer type: %s', analyzer_type)
        return analyzer

    except Exception as ex:
        LOG.debug_analyzer(ex)
        return None


def build_config_handlers(args, context, enabled_analyzers):
    """
    Handle config from command line or from config file if no command line
    config is given.

    Supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python.
    """

    analyzer_config_map = {}

    for ea in enabled_analyzers:
        config_handler = supported_analyzers[ea].\
            construct_config_handler(args, context)
        analyzer_config_map[ea] = config_handler

    return analyzer_config_map
