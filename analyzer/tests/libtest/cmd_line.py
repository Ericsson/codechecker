# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

import argparse
from codechecker_analyzer.cli import analyze


class NoExitArgumentParser(argparse.ArgumentParser):
    """
    ArgumentParser that does not exit on error.
    """
    def error(self, _):
        pass


def create_analyze_argparse(args=None):
    """
    Create argparse object for analyze command.

    :param args: list of command line arguments to parse.
    """
    if args is None:
        args = []

    parser = NoExitArgumentParser()
    analyze.add_arguments_to_parser(parser)

    return parser.parse_args(args)
