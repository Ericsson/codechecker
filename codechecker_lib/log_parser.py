# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

import os
import sys

from codechecker_lib import build_action
from codechecker_lib import logger
from codechecker_lib import option_parser

LOG = logger.get_new_logger('LOG PARSER')


# -----------------------------------------------------------------------------
def parse_compile_commands_json(logfile):
    import json

    actions = []
    filtered_build_actions = {}

    logfile.seek(0)
    data = json.load(logfile)

    counter = 0
    for entry in data:
        sourcefile = entry['file']
        lang = option_parser.get_language(sourcefile[sourcefile.rfind('.'):])

        if not lang:
            continue

        action = build_action.BuildAction(counter)

        command = entry['command']
        results = option_parser.parse_options(command)

        action.original_command = command
        action.analyzer_options = results.compile_opts
        action.lang = results.lang
        action.target = results.arch

        if results.action == option_parser.ActionType.COMPILE or \
           results.action == option_parser.ActionType.LINK:
            action.skip = False

        # TODO: check arch
        action.directory = entry['directory']

        action.sources = sourcefile
        action.lang = lang

        # filter out duplicate compilation commands
        unique_key = action.cmp_key
        if filtered_build_actions.get(unique_key) is None:
            filtered_build_actions[unique_key] = action

        del action
        counter += 1

    for ba_hash, ba in filtered_build_actions.iteritems():
        actions.append(ba)

    return actions


# -----------------------------------------------------------------------------
def parse_log(logfilepath):
    LOG.info('Parsing log file: ' + logfilepath)

    actions = []

    with open(logfilepath) as logfile:
        try:
            actions = parse_compile_commands_json(logfile)
        except (ValueError, KeyError, TypeError) as ex:
            if os.stat(logfilepath).st_size == 0:
                LOG.error('The compile database is empty.')
            else:
                LOG.error('The compile database is not valid.')
            raise ex

    LOG.info('Parsing log file done.')
    return actions
