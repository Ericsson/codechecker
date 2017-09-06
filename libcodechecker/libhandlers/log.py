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

import argparse
import os

from libcodechecker import generic_package_context
from libcodechecker.log import build_manager
from libcodechecker.log.host_check import check_intercept
from libcodechecker.logger import add_verbose_arguments


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

    parser.add_argument('-q', '--quiet-build',
                        dest="quiet_build",
                        action='store_true',
                        default=argparse.SUPPRESS,
                        required=False,
                        help="Do not print the output of the build tool into "
                             "the output of this command.")

    add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Generates a build log by running the original build command.
    No analysis is done.
    """
    args.logfile = os.path.realpath(args.logfile)
    if os.path.exists(args.logfile):
        os.remove(args.logfile)

    context = generic_package_context.get_context()
    build_manager.perform_build_command(args.logfile,
                                        args.command,
                                        context,
                                        silent='quiet_build' in args)
