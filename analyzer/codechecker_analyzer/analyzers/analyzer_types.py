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
import subprocess
import sys

from codechecker_analyzer import analyzer_context
from codechecker_common.logger import get_logger

from .. import host_check

from .clangtidy.analyzer import ClangTidy
from .clangsa.analyzer import ClangSA
from .cppcheck.analyzer import Cppcheck
from .gcc.analyzer import Gcc
from .infer.analyzer import Infer

LOG = get_logger('analyzer')

supported_analyzers = {ClangSA.ANALYZER_NAME: ClangSA,
                       ClangTidy.ANALYZER_NAME: ClangTidy,
                       Cppcheck.ANALYZER_NAME: Cppcheck,
                       Gcc.ANALYZER_NAME: Gcc,
                       Infer.ANALYZER_NAME: Infer
                       }


def is_ctu_capable():
    """ Detects if the current clang is CTU compatible. """
    enabled_analyzers, _ = check_supported_analyzers([ClangSA.ANALYZER_NAME])
    if not enabled_analyzers:
        return False

    return ClangSA.ctu_capability().is_ctu_capable


def is_ctu_on_demand_available():
    """ Detects if the current clang is capable of on-demand AST loading. """
    enabled_analyzers, _ = check_supported_analyzers([ClangSA.ANALYZER_NAME])
    if not enabled_analyzers:
        return False

    return ClangSA.ctu_capability().is_on_demand_ctu_available


def is_statistics_capable():
    """ Detects if the current clang is Statistics compatible. """
    # Resolve potentially missing binaries.
    enabled_analyzers, _ = check_supported_analyzers([ClangSA.ANALYZER_NAME])
    if not enabled_analyzers:
        return False

    checkers = ClangSA.get_analyzer_checkers(alpha=True, debug=True)

    stat_checkers_pattern = re.compile(r'.+statisticscollector.+')

    for checker_name, _ in checkers:
        if stat_checkers_pattern.match(checker_name):
            return True

    return False


def is_z3_capable():
    """ Detects if the current clang is Z3 compatible. """
    enabled_analyzers, _ = check_supported_analyzers([ClangSA.ANALYZER_NAME])
    if not enabled_analyzers:
        return False

    return host_check.has_analyzer_option(ClangSA.analyzer_binary(),
                                          ['-Xclang',
                                           '-analyzer-constraints=z3'])


def is_z3_refutation_capable():
    """ Detects if the current clang is Z3 refutation compatible. """

    # This function basically checks whether the corresponding analyzer config
    # option exists i.e. it is visible on analyzer config option help page.
    # However, it doesn't mean that Clang itself is compiled with Z3.
    if not is_z3_capable():
        return False

    check_supported_analyzers([ClangSA.ANALYZER_NAME])

    return host_check.has_analyzer_config_option(ClangSA.analyzer_binary(),
                                                 'crosscheck-with-z3')


def is_ignore_conflict_supported():
    """
    Detects if clang-apply-replacements supports --ignore-insert-conflict flag.
    """
    context = analyzer_context.get_context()
    proc = subprocess.Popen([context.replacer_binary, '--help'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            env=context
                            .get_env_for_bin(
                                context.replacer_binary),
                            encoding="utf-8", errors="ignore")
    out, _ = proc.communicate()
    return '--ignore-insert-conflict' in out


def print_unsupported_analyzers(errored):
    """ Print error messages which occured during analyzer detection. """
    for analyzer_binary, reason in errored:
        LOG.warning("Analyzer '%s' is enabled but CodeChecker failed to "
                    "execute analysis with it: '%s'. Please check your "
                    "'PATH' environment variable and the "
                    "'config/package_layout.json' file!",
                    analyzer_binary, reason)


def check_available_analyzers(args_analyzers=None):
    """
    Handle use case when no analyzer can be found or a supported, explicitly
    given analyzer cannot be found on the user machine.
    """

    if args_analyzers:
        analyzers, errored = check_supported_analyzers(args_analyzers)
        if errored:
            print_unsupported_analyzers(errored)
            LOG.error("Failed to run command because the given analyzer(s) "
                      "cannot be found on your machine!")
            sys.exit(1)

    else:
        analyzers, errored = check_supported_analyzers(supported_analyzers)
        if not analyzers:
            print_unsupported_analyzers(errored)
            LOG.error("Failed to run command because no analyzers can be "
                      "found on your machine!")
            sys.exit(1)
    return analyzers, errored


def check_supported_analyzers(analyzers):
    """
    Checks the given analyzers in the current context for their executability
    and support in CodeChecker.

    This method also updates the given context.analyzer_binaries if the
    context's configuration is bogus but had been resolved.

    :return: (enabled, failed) where enabled is a list of analyzer names
     and failed is a list of (analyzer, reason) tuple.
    """

    context = analyzer_context.get_context()

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
                resolve_missing_binary(analyzer_bin,
                                       context.get_env_for_bin(analyzer_bin))

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
            error = analyzer.is_binary_version_incompatible()
            if error:
                failed_analyzers.add((analyzer_name,
                                      f"Incompatible version: {error} "
                                      "Maybe try setting an absolute path to "
                                      "a different analyzer binary via the "
                                      "env variable CC_ANALYZER_BIN?"))
                available_analyzer = False

        if not analyzer_bin or \
           not host_check.check_analyzer(analyzer_bin):
            # Analyzers unavailable under absolute paths are deliberately a
            # configuration problem.
            failed_analyzers.add((analyzer_name,
                                  "Cannot execute analyzer binary!"))
            available_analyzer = False

        if available_analyzer:
            enabled_analyzers.add(analyzer_name)

    return enabled_analyzers, failed_analyzers


def construct_analyzer(buildaction, analyzer_config):
    analyzer_type = buildaction.analyzer_type

    LOG.debug_analyzer('Constructing %s analyzer.', analyzer_type)
    if analyzer_type in supported_analyzers:
        analyzer = \
            supported_analyzers[analyzer_type](analyzer_config, buildaction)
    else:
        analyzer = None
        LOG.error('Unsupported analyzer type: %s', analyzer_type)
    return analyzer


def build_config_handlers(args, enabled_analyzers):
    """
    Handle config from command line or from config file if no command line
    config is given.

    Supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python.
    """

    analyzer_config_map = {}

    for ea in enabled_analyzers:
        assert supported_analyzers[ea].analyzer_binary(), \
            "At this point, we should've checked if this analyzer has a " \
            "binary!"
        config_handler = supported_analyzers[ea].construct_config_handler(args)
        analyzer_config_map[ea] = config_handler

    return analyzer_config_map
