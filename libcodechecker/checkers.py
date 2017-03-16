# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
List the checkers available in the analyzers.
"""

import argparse
import sys

from libcodechecker import generic_package_context
from libcodechecker.analyze import analyzer_env
from libcodechecker.analyze.analyzers import analyzer_types
from libcodechecker.logger import add_verbose_arguments
from libcodechecker.logger import LoggerFactory

LOG = LoggerFactory.get_new_logger('CHECKERS')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker checkers',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Get the list of checkers available in the supported"
                       " analyzers. Currently supported analyzers are: " +
                       ', '.join(list(analyzer_types.supported_analyzers)) +
                       ".",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "List the checkers available in code analysis."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('--analyzers', nargs='+',
                        dest="analyzers", required=False,
                        help='Select which analyzer checkers '
                             'should be listed.\nCurrently supported '
                             'analyzers:\n')

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    List the supported checkers by the analyzers.
    List the default enabled and disabled checkers in the config.
    """
    context = generic_package_context.get_context()
    # If nothing is set, list checkers for all supported analyzers.
    analyzers = args.analyzers or analyzer_types.supported_analyzers
    enabled_analyzers, failed_analyzers = analyzer_types \
        .check_supported_analyzers(analyzers, context)
    analyzer_environment = analyzer_env.get_check_env(
        context.path_env_extra,
        context.ld_lib_path_extra)

    for ea in enabled_analyzers:
        if ea not in analyzer_types.supported_analyzers:
            LOG.error('Unsupported analyzer ' + str(ea))
            sys.exit(1)

    analyzer_config_map = \
        analyzer_types.build_config_handlers(args,
                                             context,
                                             enabled_analyzers)

    for ea in enabled_analyzers:
        # Get the config.
        config_handler = analyzer_config_map.get(ea)
        source_analyzer = \
            analyzer_types.construct_analyzer_type(ea,
                                                   config_handler,
                                                   None)

        checkers = source_analyzer.get_analyzer_checkers(config_handler,
                                                         analyzer_environment)

        default_checker_cfg = context.default_checkers_config.get(
            ea + '_checkers')

        analyzer_types.initialize_checkers(config_handler,
                                           checkers,
                                           default_checker_cfg)
        for checker_name, value in config_handler.checks().items():
            enabled, description = value
            if enabled:
                print(' + {0:50} {1}'.format(checker_name, description))
            else:
                print(' - {0:50} {1}'.format(checker_name, description))

    for analyzer_binary, reason in failed_analyzers:
        LOG.error("Failed to get checkers for '" + analyzer_binary +
                  "'! The error reason was: '" + reason + "'")
        LOG.error("Please check your installation and the "
                  "'config/package_layout.json' file!")
