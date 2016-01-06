# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

"""
supported analyzer types
"""
import os
import re
import sys

from codechecker_lib import logger
from codechecker_lib import analyzer_env
from codechecker_lib import host_check
from codechecker_lib import client

from codechecker_lib.analyzers import analyzer_clangsa
from codechecker_lib.analyzers import config_handler_clangsa
from codechecker_lib.analyzers import result_handler_clangsa

from codechecker_lib.analyzers import analyzer_clang_tidy
from codechecker_lib.analyzers import result_handler_clang_tidy
from codechecker_lib.analyzers import config_handler_clang_tidy

LOG = logger.get_new_logger('ANALYZER TYPES')


CLANG_SA = 'ClangSA'
CLANG_TIDY = 'Clang-tidy'

supported_analyzers = {CLANG_SA, CLANG_TIDY}

def is_sa_checker_name(checker_name):
    """
    match for Clang Static analyzer names like

    unix
    unix.Malloc
    security.insecureAPI
    security.insecureAPI.gets
    """
    # no '-' is alowed in the checker name
    sa_checker_name = r'^[^-]+$'
    ptn = re.compile(sa_checker_name)

    if ptn.match(checker_name):
        return True
    return False

def is_tidy_checker_name(checker_name):
    """
    match for Clang Tidy analyzer names like

    -*
    modernize-*
    clang-diagnostic-*
    cert-fio38-c
    google-global-names-in-headers
    """
    # must contain at least one '-'
    tidy_checker_name = r'^(?=.*[\-]).+$'

    ptn = re.compile(tidy_checker_name)

    if ptn.match(checker_name):
        return True
    return False


def check_supported_analyzers(analyzers, context):
    """
    check if the selected analyzers are supported
    """

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = set()

    if not analyzers:
        # no analyzer is set clang static analyzer will be the default
        enabled_analyzers.add(CLANG_SA)
        name = CLANG_SA
        # check if clangSA can run
        analyzer_bin = analyzer_binaries.get(name)
        if not analyzer_bin:
            LOG.error('Failed to detect analyzer binary ' + name)
        if not host_check.check_clang(analyzer_bin, check_env):
            LOG.error('Failed to start analyzer: ' + name + ' !')
            sys.exit(1)
    else:
        for analyzer_name in analyzers:
            if analyzer_name not in supported_analyzers:
                LOG.error('Unsupported analyzer ' + analyzer_name + ' !')
                sys.exit(1)
            else:
                # get the compiler binary to check if it can run
                analyzer_bin = analyzer_binaries.get(analyzer_name)
                if not analyzer_bin:
                    LOG.error('Failed to detect analyzer binary ' + analyzer_name)
                if not host_check.check_clang(analyzer_bin, check_env):
                    LOG.error('Failed to get version for analyzer '
                              + analyzer_name + ' !')
                    sys.exit(1)
                enabled_analyzers.add(analyzer_name)

    return enabled_analyzers


def construct_analyzer_type(analyzer_type, config_handler, buildaction):
    """
    construct a specific analyzer based on the type
    """

    if analyzer_type == CLANG_SA:
        LOG.debug('Constructing clangSA analyzer')

        analyzer = analyzer_clangsa.ClangSA(config_handler,
                                            buildaction)

        return analyzer

    elif analyzer_type == CLANG_TIDY:
        LOG.debug("Constructing clang-tidy analyzer")

        analyzer = analyzer_clang_tidy.ClangTidy(config_handler,
                                                 buildaction)

        return analyzer
    else:
        LOG.error('Not supported analyzer type')
        return None


def construct_analyzer(buildaction,
                       analyzer_config_map):
    """
    construct an analyzer
    """
    try:
        LOG.debug('Constructing analyzer')
        analyzer_type = buildaction.analyzer_type
        # get the proper config handler for this analyzer type
        config_handler = analyzer_config_map.get(analyzer_type)

        analyzer = construct_analyzer_type(analyzer_type,
                                           config_handler,
                                           buildaction)
        return analyzer

    except Exception as ex:
        LOG.debug(ex)
        return None


def __build_clangsa_config_handler(args, context):
    """
    Build the config handler for clang static analyzer
    Handle config options from the command line and config files
    """

    config_handler = config_handler_clangsa.ClangSAConfigHandler()
    config_handler.analyzer_plugins_dir = context.checker_plugin
    analyzer_name = CLANG_SA
    config_handler.analyzer_binary = context.analyzer_binaries.get(analyzer_name)
    config_handler.compiler_resource_dirs = context.compiler_resource_dirs
    config_handler.compiler_sysroot = context.compiler_sysroot
    config_handler.system_includes = context.extra_system_includes
    config_handler.includes = context.extra_includes
    try:
        with open(args.clangsa_args_cfg_file, 'rb') as sa_cfg:
            config_handler.analyzer_extra_arguments = sa_cfg.read().strip()
    except IOError as ioerr:
        LOG.debug(ioerr)
    except AttributeError as aerr:
        # no clangsa arguments file was given in the command line
        LOG.debug(aerr)

    # read clangsa checkers from the package config file
    clang_sa_checkers = context.default_checkers_config.get('clangsa_checkers')

    if clang_sa_checkers:
        for data in clang_sa_checkers:
            config_handler.add_checks(data.items())

    # add user defined checkers form the command line
    try:
        config_handler.add_checks(args.clang_sa_ordered_checker_args)
    except AttributeError:
        LOG.debug('No checkers were defined in the command line for clangSA')

    LOG.debug(config_handler.checks())

    return config_handler


def __build_clang_tidy_config_handler(args, context):
    """
    Build the config handler for clang tidy analyzer
    Handle config options from the command line and config files
    """

    config_handler = config_handler_clang_tidy.ClangTidyConfigHandler()
    analyzer_name = CLANG_TIDY
    config_handler.analyzer_binary = context.analyzer_binaries.get(analyzer_name)
    config_handler.compiler_resource_dirs = context.compiler_resource_dirs
    config_handler.compiler_sysroot = context.compiler_sysroot
    config_handler.system_includes = context.extra_system_includes
    config_handler.includes = context.extra_includes

    try:
        with open(args.tidy_args_cfg_file, 'rb') as tidy_cfg:
            config_handler.analyzer_extra_arguments = tidy_cfg.read().strip()
    except IOError as ioerr:
        LOG.debug(ioerr)
    except AttributeError as aerr:
        # no clang tidy arguments file was given in the command line
        LOG.debug(aerr)

    # extend analyzer config with
    # read clang-tidy checkers from the config file
    clang_tidy_checkers = context.default_checkers_config.get('clang_tidy_checkers')

    if clang_tidy_checkers:
        for data in clang_tidy_checkers:
            config_handler.add_checks(data.items())

    # add user defined checkers form the command line
    try:
        config_handler.add_checks(args.clang_tidy_ordered_checker_args)
    except AttributeError:
        LOG.debug('No checkers were defined in the command line for Clang tidy')

    return config_handler


def build_config_handlers(args, context, enabled_analyzers, connection=None):
    """
    construct multiple config handlers and if there is a connection
    store configs into the database

    handle config from command line or from config file if no command line
    config is given

    supported command line config format is in JSON tidy supports YAML also but
    no standard lib for yaml parsing is available in python

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
            LOG.debug('Not supported analyzer type. No configuration handler will be created')

    if connection:
        # collect all configuration options and store them together
        configs = []
        for _, config_handler in analyzer_config_map.iteritems():
            configs.extend(config_handler.get_checker_configs())

        client.replace_config_in_db(run_id, connection, configs)

    return analyzer_config_map


def construct_result_handler(args,
                             buildaction,
                             run_id,
                             report_output,
                             severity_map,
                             skiplist_handler,
                             store_to_db=False):
    """
    construct a result handler
    """

    if store_to_db:
        # create a result handler which stores the results into a database
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
            LOG.error('Not supported analyzer type')
            return None
    else:
        if buildaction.analyzer_type == CLANG_SA:
            csa_res_handler = result_handler_clangsa.ClangSAPlistToStdout(
                buildaction,
                report_output)

            csa_res_handler.print_steps = args.print_steps
            return csa_res_handler

        elif buildaction.analyzer_type == CLANG_TIDY:
            ct_res_handler = result_handler_clang_tidy.ClangTidyPlistToStdout(
                buildaction,
                report_output)

            ct_res_handler.severity_map = severity_map
            ct_res_handler.skiplist_handler = skiplist_handler
            return ct_res_handler
        else:
            LOG.error('Not supported analyzer type')
            return None
