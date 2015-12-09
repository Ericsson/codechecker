# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
''''''
import os
import sys
import json
import time

import shared

from codechecker_lib import client
from codechecker_lib import logger
from codechecker_lib import analyzer_env
from codechecker_lib import host_check
from codechecker_lib import analysis_manager
from codechecker_lib import skiplist_handler

from codechecker_lib.analyzers import analyzer_types

LOG = logger.get_new_logger('ANALYZER')


def check_supported_analyzers(analyzers, context):
    """
    check if the selected analyzers are supported
    """

    check_env = analyzer_env.get_check_env(context.path_env_extra,
                                           context.ld_lib_path_extra)

    analyzer_binaries = context.analyzer_binaries

    enabled_analyzers = []

    if not analyzers:
        # no analyzer is set clang static analyzer will be the default
        enabled_analyzers.append(analyzer_types.CLANG_SA)
        name = analyzer_types.get_analyzer_type_name(analyzer_types.CLANG_SA)
        # check if clangSA can run
        analyzer_bin = analyzer_binaries.get(name)
        if not host_check.check_clang(analyzer_bin, check_env):
            LOG.error('Failed to start analyzer: ' + name + ' !')
            sys.exit(1)
    else:
        for analyzer_name in analyzers:
            if analyzer_name not in analyzer_types.analyzer_type_name_map.keys():
                LOG.error('Unsupported analyzer ' + analyzer_name +' !')
                sys.exit(1)
            else:
                # get the compiler binary to check if it can run
                analyzer_type = analyzer_types.analyzer_type_name_map.get(analyzer_name)
                analyzer_bin = analyzer_binaries.get(analyzer_name)
                if not host_check.check_clang(analyzer_bin, check_env):
                    LOG.error('Failed to get version for analyzer ' + analyzer_name +' !')
                    sys.exit(1)
                enabled_analyzers.append(analyzer_type)

    return enabled_analyzers


def run_check(args, actions, context):
    """
    prepares the buildactions and required configuration
    files for the analysis

    stores analysis related data to the database
    """

    if args.jobs <= 0:
        args.jobs = 1

    LOG.debug("Checking supported analyzers.")
    enabled_analyzers = check_supported_analyzers(args.analyzers,
                                                  context)

    # load severity map from config file
    LOG.debug("Loading checker severity map.")
    if os.path.exists(context.checkers_severity_map_file):
        with open(context.checkers_severity_map_file, 'r') as sev_conf_file:
            severity_config = sev_conf_file.read()

        context.severity_map = json.loads(severity_config)

    actions = analysis_manager.prepare_actions(actions, enabled_analyzers)

    analyzer_config_map = {}

    package_version = context.version['major'] + '.' + context.version['minor']

    suppress_file = os.path.join(args.workspace, package_version) \
                       if not args.suppress \
                       else os.path.realpath(args.suppress)


    with client.get_connection() as connection:
        try:
            context.run_id = connection.add_checker_run(' '.join(sys.argv),
                                                        args.name,
                                                        package_version,
                                                        args.update)

        except shared.ttypes.RequestFailed as thrift_ex:
            violation_msg = 'violates unique constraint "uq_runs_name"'
            if violation_msg not in thrift_ex.message:
                # not the unique name was the problem
                raise
            else:
                LOG.info("Name was already used in the database please choose another unique name for checking.")
                sys.exit(1)

        if args.update:
            # clean previous suppress information
            client.clean_suppress(connection, context.run_id)

        if os.path.exists(suppress_file):
            client.send_suppress(context.run_id, connection, suppress_file)

        analyzer_config_map = analysis_manager.get_config_handler(args,
                                                                  context,
                                                                  enabled_analyzers,
                                                                  connection)

    # Create one skip list handler shared between the analysis manager workers
    skp_handler = None
    if args.skipfile:
        LOG.debug("Creating skiplist handler.")
        skp_handler = skiplist_handler.SkipListHandler(args.skipfile)
        connection.add_skip_paths(context.run_id, skp_handler.get_skiplist())

    LOG.info("Static analysis is starting ...")
    start_time = time.time()

    analysis_manager.start_workers(args,
                                   actions,
                                   context,
                                   analyzer_config_map,
                                   skp_handler)

    end_time = time.time()

    with client.get_connection() as connection:
        connection.finish_checker_run(context.run_id)

    LOG.info("Analysis length: " + str(end_time - start_time) + " sec.")


def run_quick_check(args,
                    context,
                    actions):
    '''
    This function implements the "quickcheck" feature.
    No result is stored to a database
    '''

    enabled_analyzers = []

    enabled_analyzers = check_supported_analyzers(args.analyzers,
                                                  context)

    actions = analysis_manager.prepare_actions(actions, enabled_analyzers)

    analyzer_config_map = {}

    analyzer_config_map = analysis_manager.get_config_handler(args,
                                                              context,
                                                              enabled_analyzers)

    for action in actions:
        check_data = (args,
                      action,
                      context,
                      analyzer_config_map,
                      None,
                      args.workspace,
                      False,
                      args.keep_tmp)

        analysis_manager.check(check_data)
