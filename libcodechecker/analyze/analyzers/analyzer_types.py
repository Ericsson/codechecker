# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Supported analyzer types.
"""
import os
import platform
import re
import sys

from libcodechecker import client
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze import host_check
from libcodechecker.analyze.analyzers import analyzer_clang_tidy
from libcodechecker.analyze.analyzers import analyzer_clangsa
from libcodechecker.analyze.analyzers import config_handler_clang_tidy
from libcodechecker.analyze.analyzers import config_handler_clangsa
from libcodechecker.analyze.analyzers import result_handler_base
from libcodechecker.analyze.analyzers import result_handler_clang_tidy
from libcodechecker.analyze.analyzers import result_handler_plist_to_db
from libcodechecker.analyze.analyzers import result_handler_plist_to_stdout
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('ANALYZER TYPES')

CLANG_SA = 'clangsa'
CLANG_TIDY = 'clang-tidy'

supported_analyzers = {CLANG_SA, CLANG_TIDY}


def is_sa_checker_name(checker_name):
    """
    Match for Clang Static analyzer names like:
    - unix
    - unix.Malloc
    - security.insecureAPI
    - security.insecureAPI.gets
    """
    # No '-' is allowed in the checker name.
    sa_checker_name = r'^[^-]+$'
    ptn = re.compile(sa_checker_name)

    return ptn.match(checker_name) is not None


def is_tidy_checker_name(checker_name):
    """
    Match for Clang Tidy analyzer names like:
        -*
        modernize-*
        clang-diagnostic-*
        cert-fio38-c
        google-global-names-in-headers
    """
    # Must contain at least one '-'.
    tidy_checker_name = r'^(?=.*[\-]).+$'

    ptn = re.compile(tidy_checker_name)

    return ptn.match(checker_name) is not None


def check_supported_analyzers(analyzers, context):
    """
    Checks the given analyzers in the current context for their executability
    and support in CodeChecker.

    This method also updates the given context.analyzer_binaries if the
    context's configuration is bogus but had been resolved.

    :return: (enabled, failed) where enabled is a list of analyzer names
     and failed is a list of (analyzer, reason) tuple.
    """

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = set()
    failed_analyzers = set()

    for analyzer_name in analyzers:
        if analyzer_name not in supported_analyzers:
            failed_analyzers.add((analyzer_name,
                                  "Analyzer unsupported by CodeChecker."))

        # Get the compiler binary to check if it can run.
        available_analyzer = True
        analyzer_bin = analyzer_binaries.get(analyzer_name)
        if not analyzer_bin:
            failed_analyzers.add((analyzer_name,
                                  "Failed to detect analyzer binary."))
            available_analyzer = False
        elif not os.path.isabs(analyzer_bin):
            # If the analyzer is not in an absolute path, try to find it...
            if analyzer_name == CLANG_SA:
                found_bin = analyzer_clangsa.ClangSA. \
                    resolve_missing_binary(analyzer_bin, check_env)
            elif analyzer_name == CLANG_TIDY:
                found_bin = analyzer_clang_tidy.ClangTidy. \
                    resolve_missing_binary(analyzer_bin, check_env)

            # found_bin is an absolute path, an executable in one of the
            # PATH folders.
            # If found_bin is the same as the original binary, ie., normally
            # calling the binary without any search would have resulted in
            # the same binary being called, it's NOT a "not found".
            if found_bin and os.path.basename(found_bin) != analyzer_bin:
                LOG.debug("Configured binary '{0}' for analyzer '{1}' was "
                          "not found, but environment PATH contains '{2}'."
                          .format(analyzer_bin, analyzer_name, found_bin))
                context.analyzer_binaries[analyzer_name] = found_bin

            if not found_bin or \
                    not host_check.check_clang(found_bin, check_env):
                # If analyzer_bin is not False here, the resolver found one.
                failed_analyzers.add((analyzer_name,
                                      "Couldn't run analyzer binary."))
                available_analyzer = False
        elif not host_check.check_clang(analyzer_bin, check_env):
            # Analyzers unavailable under absolute paths are deliberately a
            # configuration problem.
            failed_analyzers.add((analyzer_name,
                                  "Cannot execute analyzer binary."))
            available_analyzer = False

        if available_analyzer:
            enabled_analyzers.add(analyzer_name)

    return enabled_analyzers, failed_analyzers


def construct_analyzer_type(analyzer_type, config_handler, buildaction):
    """
    Construct a specific analyzer based on the type.
    """

    LOG.debug_analyzer('Constructing ' + analyzer_type + '  analyzer')
    if analyzer_type == CLANG_SA:
        analyzer = analyzer_clangsa.ClangSA(config_handler,
                                            buildaction)
        return analyzer

    elif analyzer_type == CLANG_TIDY:
        analyzer = analyzer_clang_tidy.ClangTidy(config_handler,
                                                 buildaction)
        return analyzer
    else:
        LOG.error('Unsupported analyzer type: ' + analyzer_type)
        return None


def construct_analyzer(buildaction,
                       analyzer_config_map):
    """
    Construct an analyzer.
    """
    try:
        analyzer_type = buildaction.analyzer_type
        # Get the proper config handler for this analyzer type.
        config_handler = analyzer_config_map.get(analyzer_type)

        analyzer = construct_analyzer_type(analyzer_type,
                                           config_handler,
                                           buildaction)
        return analyzer

    except Exception as ex:
        LOG.debug_analyzer(ex)
        return None


def initialize_checkers(config_handler,
                        checkers,
                        default_checkers=None,
                        cmdline_checkers=None,
                        enable_all=False):
    """
    Initializes the checker list for the specified config handler based
    on the given defaults, commandline arguments and analyzer-retriever
    checker list.
    """

    # By default disable all checkers.
    for checker_name, description in checkers:
        config_handler.add_checker(checker_name, False, description)

    # Set default enabled or disabled checkers, retrieved from a config file.
    if default_checkers:
        for checker in default_checkers:
            for checker_name, enabled in checker.items():
                if enabled:
                    config_handler.enable_checker(checker_name)
                else:
                    config_handler.disable_checker(checker_name)

    # If enable_all is given, almost all checkers should be enabled.
    if enable_all:
        for checker_name, enabled in checkers:
            if not checker_name.startswith("alpha.") and \
                    not checker_name.startswith("debug.") and \
                    not checker_name.startswith("osx."):
                # There are a few exceptions, though, which still need to
                # be manually enabled by the user: alpha and debug.
                config_handler.enable_checker(checker_name)

            if checker_name.startswith("osx.") and \
                    platform.system() == 'Darwin':
                # OSX checkers are only enable-all'd if we are on OSX.
                config_handler.enable_checker(checker_name)

    # Set user defined enabled or disabled checkers from the command line.
    if cmdline_checkers:
        for checker_name, enabled in cmdline_checkers:
            if enabled:
                config_handler.enable_checker(checker_name)
            else:
                config_handler.disable_checker(checker_name)


def __replace_env_var(cfg_file):
    def replacer(matchobj):
        env_var = matchobj.group(1)
        if matchobj.group(1) not in os.environ:
            LOG.error(env_var + ' environment variable not set in ' + cfg_file)
            return ''
        return os.environ[env_var]

    return replacer


def __build_clangsa_config_handler(args, context):
    """
    Build the config handler for clang static analyzer.
    Handle config options from the command line and config files.
    """

    config_handler = config_handler_clangsa.ClangSAConfigHandler()
    config_handler.analyzer_plugins_dir = context.checker_plugin
    config_handler.analyzer_binary = context.analyzer_binaries.get(CLANG_SA)
    config_handler.compiler_resource_dir = context.compiler_resource_dir
    config_handler.compiler_sysroot = context.compiler_sysroot
    config_handler.system_includes = context.extra_system_includes
    config_handler.includes = context.extra_includes
    try:
        with open(args.clangsa_args_cfg_file, 'rb') as sa_cfg:
            config_handler.analyzer_extra_arguments = \
                re.sub('\$\((.*?)\)',
                       __replace_env_var(args.clangsa_args_cfg_file),
                       sa_cfg.read().strip())
    except IOError as ioerr:
        LOG.debug_analyzer(ioerr)
    except AttributeError as aerr:
        # No clangsa arguments file was given in the command line.
        LOG.debug_analyzer(aerr)

    analyzer = construct_analyzer_type(CLANG_SA, config_handler, None)

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    checkers = analyzer.get_analyzer_checkers(config_handler, check_env)

    # Read clang-sa checkers from the config file.
    clang_sa_checkers = context.default_checkers_config.get(CLANG_SA +
                                                            '_checkers')
    try:
        cmdline_checkers = args.ordered_checkers
    except AttributeError:
        LOG.debug_analyzer('No checkers were defined in '
                           'the command line for ' + CLANG_SA)
        cmdline_checkers = None

    initialize_checkers(config_handler,
                        checkers,
                        clang_sa_checkers,
                        cmdline_checkers,
                        'enable_all' in args and args.enable_all)

    return config_handler


def __build_clang_tidy_config_handler(args, context):
    """
    Build the config handler for clang tidy analyzer.
    Handle config options from the command line and config files.
    """

    config_handler = config_handler_clang_tidy.ClangTidyConfigHandler()
    config_handler.analyzer_binary = context.analyzer_binaries.get(CLANG_TIDY)
    config_handler.compiler_resource_dir = context.compiler_resource_dir
    config_handler.compiler_sysroot = context.compiler_sysroot
    config_handler.system_includes = context.extra_system_includes
    config_handler.includes = context.extra_includes

    try:
        with open(args.tidy_args_cfg_file, 'rb') as tidy_cfg:
            config_handler.analyzer_extra_arguments = \
                re.sub('\$\((.*?)\)', __replace_env_var,
                       tidy_cfg.read().strip())
    except IOError as ioerr:
        LOG.debug_analyzer(ioerr)
    except AttributeError as aerr:
        # No clang tidy arguments file was given in the command line.
        LOG.debug_analyzer(aerr)

    analyzer = construct_analyzer_type(CLANG_TIDY, config_handler, None)
    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    checkers = analyzer.get_analyzer_checkers(config_handler, check_env)

    # Read clang-tidy checkers from the config file.
    clang_tidy_checkers = context.default_checkers_config.get(CLANG_TIDY +
                                                              '_checkers')
    try:
        cmdline_checkers = args.ordered_checkers
    except AttributeError:
        LOG.debug_analyzer('No checkers were defined in '
                           'the command line for ' +
                           CLANG_TIDY)
        cmdline_checkers = None

    initialize_checkers(config_handler,
                        checkers,
                        clang_tidy_checkers,
                        cmdline_checkers,
                        'enable_all' in args and args.enable_all)

    return config_handler


def build_config_handlers(args, context, enabled_analyzers, connection=None):
    """
    Construct multiple config handlers and if there is a connection.
    Store configs into the database.

    Handle config from command line or from config file if no command line
    config is given.

    Supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python.
    """

    run_id = context.run_id
    analyzer_config_map = {}

    for ea in enabled_analyzers:
        if ea == CLANG_SA:
            config_handler = __build_clangsa_config_handler(args, context)
        elif ea == CLANG_TIDY:
            config_handler = __build_clang_tidy_config_handler(args, context)
        else:
            assert False, 'Analyzer types should have been checked already.'
        analyzer_config_map[ea] = config_handler

    if connection:
        # Collect all configuration options and store them together.
        configs = []
        for _, config_handler in analyzer_config_map.items():
            configs.extend(config_handler.get_checker_configs())

        client.replace_config_in_db(run_id, connection, configs)

    return analyzer_config_map


def construct_analyze_handler(buildaction,
                              report_output,
                              severity_map,
                              skiplist_handler):
    """
    Construct an empty (base) ResultHandler which is capable of returning
    analyzer worker statuses to the caller method, but does not provide
    actual parsing and processing of results, instead only saves the analysis
    results.
    """

    assert buildaction.analyzer_type in supported_analyzers, \
        'Analyzer types should have been checked already.'

    if buildaction.analyzer_type == CLANG_SA:
        res_handler = result_handler_base.ResultHandler(buildaction,
                                                        report_output)

    elif buildaction.analyzer_type == CLANG_TIDY:
        res_handler = result_handler_clang_tidy.ClangTidyPlistToFile(
            buildaction, report_output)

    res_handler.severity_map = severity_map
    res_handler.skiplist_handler = skiplist_handler
    return res_handler


def construct_parse_handler(buildaction,
                            output,
                            severity_map,
                            suppress_handler,
                            print_steps):
    """
    Construct a result handler for parsing results in a human-readable format.
    """
    assert buildaction.analyzer_type in supported_analyzers, \
        'Analyzer types should have been checked already.'

    if buildaction.analyzer_type == CLANG_SA:
        res_handler = result_handler_plist_to_stdout.PlistToStdout(
            buildaction,
            output,
            None)
        res_handler.print_steps = print_steps

    elif buildaction.analyzer_type == CLANG_TIDY:
        res_handler = result_handler_clang_tidy.ClangTidyPlistToStdout(
            buildaction,
            output,
            None)

    res_handler.severity_map = severity_map
    res_handler.suppress_handler = suppress_handler
    return res_handler


# TODO: This is deprecated.
def construct_result_handler(args,
                             buildaction,
                             run_id,
                             report_output,
                             severity_map,
                             skiplist_handler,
                             lock,
                             store_to_db=False):
    """
    Construct a result handler.
    """
    assert buildaction.analyzer_type in supported_analyzers, \
        'Analyzer types should have been checked already.'

    if store_to_db:
        # Create a result handler which stores the results into a database.
        if buildaction.analyzer_type == CLANG_SA:
            res_handler = result_handler_plist_to_db.PlistToDB(
                buildaction,
                report_output,
                run_id)

        elif buildaction.analyzer_type == CLANG_TIDY:
            res_handler = result_handler_clang_tidy.ClangTidyPlistToDB(
                buildaction,
                report_output,
                run_id)

    else:
        if buildaction.analyzer_type == CLANG_SA:
            res_handler = result_handler_plist_to_stdout.PlistToStdout(
                buildaction,
                report_output,
                lock)
            res_handler.print_steps = args.print_steps

        elif buildaction.analyzer_type == CLANG_TIDY:
            res_handler = result_handler_clang_tidy.ClangTidyPlistToStdout(
                buildaction,
                report_output,
                lock)

    res_handler.severity_map = severity_map
    res_handler.skiplist_handler = skiplist_handler
    return res_handler
