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
from codechecker_lib import analysis_manager
from codechecker_lib import skiplist_handler

from codechecker_lib.analyzers import analyzer_types

LOG = logger.get_new_logger('ANALYZER')


def run_check(args, actions, context):
    """
    prepares the buildactions and required configuration
    files for the analysis

    stores analysis related data to the database
    """

    if args.jobs <= 0:
        args.jobs = 1

    LOG.debug("Checking supported analyzers.")
    enabled_analyzers = analyzer_types.check_supported_analyzers(args.analyzers,
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

        analyzer_config_map = analyzer_types.get_config_handler(args,
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

    enabled_analyzers = analyzer_types.check_supported_analyzers(args.analyzers,
                                                                 context)

    actions = analysis_manager.prepare_actions(actions, enabled_analyzers)

    analyzer_config_map = {}

    analyzer_config_map = analyzer_types.get_config_handler(args,
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
