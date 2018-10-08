# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
'CodeChecker log' executes a build action and registers a compilation database
for the given build, using an external tool such as scan-build-py or ld-logger.

This module contains the basic definitions for how 'CodeChecker log' is to be
invoked and ran.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import os

from libcodechecker import package_context
from libcodechecker import logger
from libcodechecker.log import build_manager
from libcodechecker.log.host_check import check_intercept


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker log',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Runs the given build command and records the executed "
                       "compilation steps. These steps are written to the "
                       "output file in a JSON format.\n\nAvailable build "
                       "logger tool that will be used is '" +
                       ('intercept-build' if check_intercept(os.environ)
                        else 'ld-logger') + "'.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Run a build command and collect the executed compilation "
                "commands, storing them in a JSON file."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-o', '--output',
                        type=str,
                        dest="logfile",
                        default=argparse.SUPPRESS,
                        required=True,
                        help="Path of the file to write the collected "
                             "compilation commands to. If the file already "
                             "exists, it will be overwritten.")

    parser.add_argument('-b', '--build',
                        type=str,
                        dest="command",
                        default=argparse.SUPPRESS,
                        required=True,
                        help="The build command to execute. Build commands "
                             "can be simple calls to 'g++' or 'clang++' or "
                             "'make', but a more complex command, or the call "
                             "of a custom script file is also supported.")

    parser.add_argument('-k', '--keep-link',
                        dest="keep_link",
                        default=argparse.SUPPRESS,
                        action="store_true",
                        help="If this flag is given then the output log file "
                             "will contain the linking build actions too.")

    parser.add_argument('-q', '--quiet',
                        dest="quiet",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Do not print the output of the build tool into "
                             "the output of this command.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Generates a build log by running the original build command.
    No analysis is done.
    """
    logger.setup_logger(args.verbose if 'verbose' in args else None)

    args.logfile = os.path.realpath(args.logfile)
    if os.path.exists(args.logfile):
        os.remove(args.logfile)

    context = package_context.get_context()
    build_manager.perform_build_command(args.logfile,
                                        args.command,
                                        context,
                                        'keep_link' in args,
                                        silent='quiet' in args)
