# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
Supported analyzer types.
"""
import os
import re
import sys

from codechecker_lib import analyzer_env
from codechecker_lib import client
from codechecker_lib import host_check
from codechecker_lib import logger
from codechecker_lib.analyzers import analyzer_clang_tidy
from codechecker_lib.analyzers import analyzer_clangsa
from codechecker_lib.analyzers import config_handler_clang_tidy
from codechecker_lib.analyzers import config_handler_clangsa
from codechecker_lib.analyzers import result_handler_clang_tidy
from codechecker_lib.analyzers import result_handler_clangsa

LOG = logger.get_new_logger('ANALYZER TYPES')

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

    if ptn.match(checker_name):
        return True
    return False


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

    if ptn.match(checker_name):
        return True
    return False


def check_supported_analyzers(analyzers, context):
    """
    Check if the selected analyzers are supported.
    """

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = set()

    for analyzer_name in analyzers:
        if analyzer_name not in supported_analyzers:
            LOG.error('Unsupported analyzer ' + analyzer_name + ' !')
            sys.exit(1)

        # Get the compiler binary to check if it can run.
        available_analyzer = True
        analyzer_bin = analyzer_binaries.get(analyzer_name)
        if not analyzer_bin:
            LOG.debug_analyzer('Failed to detect analyzer binary ' +
                               analyzer_name)
            available_analyzer = False
        if not host_check.check_clang(analyzer_bin, check_env):
            LOG.warning('Failed to run analyzer ' + analyzer_name + ' !')
            available_analyzer = False
        if available_analyzer:
            enabled_analyzers.add(analyzer_name)

    return enabled_analyzers


def construct_analyzer_type(analyzer_type, config_handler, buildaction):
    """
    Construct a specific analyzer based on the type.
    """

    if analyzer_type == CLANG_SA:
        LOG.debug_analyzer('Constructing clangSA analyzer')

        analyzer = analyzer_clangsa.ClangSA(config_handler,
                                            buildaction)

        return analyzer

    elif analyzer_type == CLANG_TIDY:
        LOG.debug_analyzer("Constructing clang-tidy analyzer")

        analyzer = analyzer_clang_tidy.ClangTidy(config_handler,
                                                 buildaction)

        return analyzer
    else:
        LOG.error('Not supported analyzer type')
        return None


def construct_analyzer(buildaction,
                       analyzer_config_map):
    """
    Construct an analyzer.
    """
    try:
        LOG.debug_analyzer('Constructing analyzer')
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
                        cmdline_checkers=None):
    # By default disable all checkers.
    for checker_name, description in checkers:
        config_handler.add_checker(checker_name, False, description)

    # Set default enabled or disabled checkers.
    if default_checkers:
        for checker in default_checkers:
            for checker_name, enabled in checker.items():
                if enabled:
                    config_handler.enable_checker(checker_name)
                else:
                    config_handler.disable_checker(checker_name)

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

    # Read clang-tidy checkers from the config file.
    clang_sa_checkers = context.default_checkers_config.get(CLANG_SA +
                                                            '_checkers')
    try:
        cmdline_checkers = args.ordered_checkers
    except AttributeError:
        LOG.debug_analyzer('No checkers were defined in the command line for' +
                           CLANG_SA)
        cmdline_checkers = None

    initialize_checkers(config_handler,
                        checkers,
                        clang_sa_checkers,
                        cmdline_checkers)

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
        LOG.debug_analyzer('No checkers were defined in the command line for ' +
                           CLANG_TIDY)
        cmdline_checkers = None

    initialize_checkers(config_handler,
                        checkers,
                        clang_tidy_checkers,
                        cmdline_checkers)

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
            analyzer_config_map[ea] = config_handler

        elif ea == CLANG_TIDY:
            config_handler = __build_clang_tidy_config_handler(args, context)
            analyzer_config_map[ea] = config_handler
        else:
            LOG.debug_analyzer('Not supported analyzer type. '
                               'No configuration handler will be created.')

    if connection:
        # Collect all configuration options and store them together.
        configs = []
        for _, config_handler in analyzer_config_map.items():
            configs.extend(config_handler.get_checker_configs())

        client.replace_config_in_db(run_id, connection, configs)

    return analyzer_config_map


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

    if store_to_db:
        # Create a result handler which stores the results into a database.
        if buildaction.analyzer_type == CLANG_SA:
            csa_res_handler = result_handler_clangsa.ClangSAPlistToDB(
                buildaction,
                report_output,
                run_id)

            csa_res_handler.severity_map = severity_map
            csa_res_handler.skiplist_handler = skiplist_handler
            return csa_res_handler

        elif buildaction.analyzer_type == CLANG_TIDY:
            ct_res_handler = result_handler_clang_tidy.ClangTidyPlistToDB(
                buildaction,
                report_output,
                run_id)

            ct_res_handler.severity_map = severity_map
            ct_res_handler.skiplist_handler = skiplist_handler
            return ct_res_handler

        else:
            LOG.error('Not supported analyzer type.')
            return None
    else:
        if buildaction.analyzer_type == CLANG_SA:
            csa_res_handler = result_handler_clangsa.ClangSAPlistToStdout(
                buildaction,
                report_output,
                lock)

            csa_res_handler.print_steps = args.print_steps
            csa_res_handler.skiplist_handler = skiplist_handler
            return csa_res_handler

        elif buildaction.analyzer_type == CLANG_TIDY:
            ct_res_handler = result_handler_clang_tidy.ClangTidyPlistToStdout(
                buildaction,
                report_output,
                lock)

            ct_res_handler.severity_map = severity_map
            ct_res_handler.skiplist_handler = skiplist_handler
            return ct_res_handler
        else:
            LOG.error('Not supported analyzer type.')
            return None
