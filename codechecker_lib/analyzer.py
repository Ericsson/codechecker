# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Prepare and start different analisys types
"""
import os
import sys
import json
import time
import copy

import shared

from codechecker_lib import client
from codechecker_lib import logger
from codechecker_lib import analysis_manager
from codechecker_lib import skiplist_handler

from codechecker_lib.analyzers import analyzer_types

LOG = logger.get_new_logger('ANALYZER')

def prepare_actions(actions, enabled_analyzers):
    """
    set the analyzer type for each buildaction
    muliply actions if multiple source analyzers are set
    """
    res = []

    for ea in enabled_analyzers:
        for action in actions:
            new_action = copy.deepcopy(action)
            new_action.analyzer_type = ea
            res.append(new_action)
    return res


def run_check(args, actions, context):
    """
    prepare:
    - analyzer config handlers
    - skiplist handling
    - analyzer severity levels

    stores analysis related data to the database and starts the analysis
    """

    if args.jobs <= 0:
        args.jobs = 1

    LOG.debug("Checking supported analyzers.")
    enabled_analyzers = analyzer_types.check_supported_analyzers(
        args.analyzers,
        context)

    # load severity map from config file
    LOG.debug("Loading checker severity map.")
    if os.path.exists(context.checkers_severity_map_file):
        with open(context.checkers_severity_map_file, 'r') as sev_conf_file:
            severity_config = sev_conf_file.read()

        context.severity_map = json.loads(severity_config)

    actions = prepare_actions(actions, enabled_analyzers)

    analyzer_config_map = {}

    package_version = context.version['major'] + '.' + context.version['minor']

    suppress_file = ''
    try:
        suppress_file = os.path.realpath(args.suppress)
    except AttributeError:
        LOG.debug('Suppress file was not set in the command line')


    # Create one skip list handler shared between the analysis manager workers
    skip_handler = None
    try:
        if args.skipfile:
            LOG.debug("Creating skiplist handler.")
            skip_handler = skiplist_handler.SkipListHandler(args.skipfile)
    except AttributeError:
        LOG.debug('Skip file was not set in the command line')


    with client.get_connection() as connection:
        context.run_id = connection.add_checker_run(' '.join(sys.argv),
                                                    args.name,
                                                    package_version,
                                                    args.force)

        # clean previous suppress information
        client.clean_suppress(connection, context.run_id)

        if os.path.exists(suppress_file):
            client.send_suppress(context.run_id, connection, suppress_file)

        analyzer_config_map = analyzer_types.build_config_handlers(args,
                                                                   context,
                                                                   enabled_analyzers,
                                                                   connection)
        if skip_handler:
            connection.add_skip_paths(context.run_id,
                                      skip_handler.get_skiplist())

    LOG.info("Static analysis is starting ...")
    start_time = time.time()

    analysis_manager.start_workers(args,
                                   actions,
                                   context,
                                   analyzer_config_map,
                                   skip_handler)

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

    enabled_analyzers = set()

    enabled_analyzers = analyzer_types.check_supported_analyzers(args.analyzers,
                                                                 context)

    actions = prepare_actions(actions, enabled_analyzers)

    analyzer_config_map = {}

    analyzer_config_map = analyzer_types.build_config_handlers(args,
                                                               context,
                                                               enabled_analyzers)

    for action in actions:
        check_data = (args,
                      action,
                      context,
                      analyzer_config_map,
                      None,
                      args.workspace,
                      False)

        analysis_manager.check(check_data)
