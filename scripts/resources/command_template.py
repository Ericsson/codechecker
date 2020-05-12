# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Handler for the $COMMAND$ subcommand for CodeChecker. This module exposes
the subcommand-specific argparse.ArgumentParser definitions and the method
which should be ran as the subcommand's main method.
"""


import argparse


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker $COMMAND$',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': 'A description about the awesome $COMMAND$ command.',

        # Epilogue is shown after the arguments when the help is queried
        # directly.
        'epilog': 'Help about how one should use $COMMAND$, something...',

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': 'A shorter help to summarise what $COMMAND$ does.'
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-a', '--arg', type=str, dest="arg",
                        default=argparse.SUPPRESS,
                        required=True,
                        help='A very good argument to pass for $COMMAND$!')

    parser.set_defaults(func=main)


def main(args):
    """
    Runs the action associated with the current command.
    """
    print("Ran subcommand CodeChecker $COMMAND$ with args:")
    print(args)
