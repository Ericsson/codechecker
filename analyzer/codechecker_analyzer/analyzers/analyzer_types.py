# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Supported analyzer types.
"""


import os
import re
import sys

from codechecker_analyzer import env
from codechecker_common.logger import get_logger

from .. import host_check

from .clangtidy.analyzer import ClangTidy
from .clangsa.analyzer import ClangSA
from .cppcheck.analyzer import Cppcheck

LOG = get_logger('analyzer')

supported_analyzers = {ClangSA.ANALYZER_NAME: ClangSA,
                       ClangTidy.ANALYZER_NAME: ClangTidy,
                       Cppcheck.ANALYZER_NAME: Cppcheck}


def is_ctu_capable(context):
    """ Detects if the current clang is CTU compatible. """
    enabled_analyzers, _ = \
        check_supported_analyzers([ClangSA.ANALYZER_NAME], context)
    if not enabled_analyzers:
        return False

    clangsa_cfg = ClangSA.construct_config_handler([], context)

    return clangsa_cfg.ctu_capability.is_ctu_capable


def is_ctu_on_demand_available(context):
    """ Detects if the current clang is capable of on-demand AST loading. """
    enabled_analyzers, _ = \
        check_supported_analyzers([ClangSA.ANALYZER_NAME], context)
    if not enabled_analyzers:
        return False

    clangsa_cfg = ClangSA.construct_config_handler([], context)

    return clangsa_cfg.ctu_capability.is_on_demand_ctu_available


def is_statistics_capable(context):
    """ Detects if the current clang is Statistics compatible. """
    # Resolve potentially missing binaries.
    enabled_analyzers, _ = \
        check_supported_analyzers([ClangSA.ANALYZER_NAME], context)
    if not enabled_analyzers:
        return False

    clangsa_cfg = ClangSA.construct_config_handler([], context)

    check_env = env.extend(context.path_env_extra,
                           context.ld_lib_path_extra)

    checkers = ClangSA.get_analyzer_checkers(
        clangsa_cfg, check_env, True, True)

    stat_checkers_pattern = re.compile(r'.+statisticscollector.+')

    for checker_name, _ in checkers:
        if stat_checkers_pattern.match(checker_name):
            return True

    return False


def is_z3_capable(context):
    """ Detects if the current clang is Z3 compatible. """
    enabled_analyzers, _ = \
        check_supported_analyzers([ClangSA.ANALYZER_NAME], context)
    if not enabled_analyzers:
        return False

    analyzer_binary = context.analyzer_binaries.get(ClangSA.ANALYZER_NAME)

    analyzer_env = env.extend(context.path_env_extra,
                              context.ld_lib_path_extra)

    return host_check.has_analyzer_option(analyzer_binary,
                                          ['-Xclang',
                                           '-analyzer-constraints=z3'],
                                          analyzer_env)


def is_z3_refutation_capable(context):
    """ Detects if the current clang is Z3 refutation compatible. """

    # This function basically checks whether the corresponding analyzer config
    # option exists i.e. it is visible on analyzer config option help page.
    # However, it doesn't mean that Clang itself is compiled with Z3.
    if not is_z3_capable(context):
        return False

    check_supported_analyzers([ClangSA.ANALYZER_NAME], context)
    analyzer_binary = context.analyzer_binaries.get(ClangSA.ANALYZER_NAME)

    analyzer_env = env.extend(context.path_env_extra,
                              context.ld_lib_path_extra)

    return host_check.has_analyzer_config_option(analyzer_binary,
                                                 'crosscheck-with-z3',
                                                 analyzer_env)


def print_unsupported_analyzers(errored):
    """ Print error messages which occured during analyzer detection. """
    for analyzer_binary, reason in errored:
        LOG.warning("Analyzer '%s' is enabled but CodeChecker is failed to "
                    "execute analysis with it: '%s'. Please check your "
                    "'PATH' environment variable and the "
                    "'config/package_layout.json' file!",
                    analyzer_binary, reason)


def check_available_analyzers(analyzers, errored):
    """ Handle use case when no analyzer can be found on the user machine. """
    if analyzers:
        return

    print_unsupported_analyzers(errored)
    LOG.error("Failed to run command because no analyzers can be found on "
              "your machine!")
    sys.exit(1)


def check_supported_analyzers(analyzers, context):
    """
    Checks the given analyzers in the current context for their executability
    and support in CodeChecker.

    This method also updates the given context.analyzer_binaries if the
    context's configuration is bogus but had been resolved.

    :return: (enabled, failed) where enabled is a list of analyzer names
     and failed is a list of (analyzer, reason) tuple.
    """

    check_env = env.extend(context.path_env_extra,
                           context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = set()
    failed_analyzers = set()

    for analyzer_name in analyzers:
        if analyzer_name not in supported_analyzers:
            failed_analyzers.add((analyzer_name,
                                  "Analyzer unsupported by CodeChecker!"))
            continue

        # Get the compiler binary to check if it can run.
        available_analyzer = True
        analyzer_bin = analyzer_binaries.get(analyzer_name)
        if not analyzer_bin:
            failed_analyzers.add((analyzer_name,
                                  "Failed to detect analyzer binary!"))
            continue
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
                context.analyzer_binaries[analyzer_name] = \
                    os.path.realpath(found_bin)

            analyzer_bin = found_bin

        # Check version compatibility of the analyzer binary.
        if analyzer_bin:
            analyzer = supported_analyzers[analyzer_name]
            if not analyzer.version_compatible(analyzer_bin, check_env):
                failed_analyzers.add((analyzer_name,
                                     "Incompatible version."))
                available_analyzer = False

        if not analyzer_bin or \
           not host_check.check_analyzer(analyzer_bin, check_env):
            # Analyzers unavailable under absolute paths are deliberately a
            # configuration problem.
            failed_analyzers.add((analyzer_name,
                                  "Cannot execute analyzer binary!"))
            available_analyzer = False

        if available_analyzer:
            enabled_analyzers.add(analyzer_name)

    return enabled_analyzers, failed_analyzers


def construct_analyzer(buildaction,
                       analyzer_config):
    try:
        analyzer_type = buildaction.analyzer_type

        LOG.debug_analyzer('Constructing %s analyzer.', analyzer_type)
        if analyzer_type in supported_analyzers:
            analyzer = supported_analyzers[analyzer_type](analyzer_config,
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
