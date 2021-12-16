# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Defines a subcommand for CodeChecker which prints version information.
"""
import argparse
import json

from typing import Dict, List, Tuple
from codechecker_analyzer import analyzer_context

from codechecker_report_converter import twodim

from codechecker_common import logger
from codechecker_common.output import USER_FORMATS


LOG = logger.get_logger('system')


class Version:
    def __init__(self):
        context = analyzer_context.get_context()

        self.version = context.version
        self.build_date = context.package_build_date
        self.git_hash = context.package_git_hash
        self.git_tag = context.package_git_tag

    def to_dict(self) -> Dict[str, str]:
        """ Get version information in dictionary format. """
        return {
            "base_package_version": self.version,
            "package_build_date": self.build_date,
            "git_commit": self.git_hash,
            "git_tag": self.git_tag}

    def to_list(self) -> List[Tuple[str, str]]:
        """ Get version information in list format. """
        return [
            ("Base package version", self.version),
            ("Package build date", self.build_date),
            ("Git commit ID (hash)", self.git_hash),
            ("Git tag information", self.git_tag)]

    def print(self, output_format: str):
        """ Print analyzer version information in the given format. """
        if output_format == "json":
            print(json.dumps(self.to_dict()))
        else:
            LOG.info("CodeChecker analyzer version:")
            print(twodim.to_str(
                output_format, ["Kind", "Version"], self.to_list()))


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker analyzer version',
        'formatter_class': argparse.ArgumentDefaultsHelpFormatter,

        # Description is shown when the command's help is queried directly
        'description': "Print the version of CodeChecker analyzer package "
                       "that is being used.",

        # Help is shown when the "parent" CodeChecker command lists the
        # individual subcommands.
        'help': "Print the version of CodeChecker analyzer package that is "
                "being used."
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('-o', '--output',
                        dest='output_format',
                        required=False,
                        default='table',
                        choices=USER_FORMATS,
                        help="The format to use when printing the version.")

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def main(args):
    """
    Get and print the version information from the version config
    file and Thrift API definition.
    """
    # If the given output format is not 'table', redirect logger's output to
    # the stderr.
    stream = None
    if 'output_format' in args and args.output_format != 'table':
        stream = 'stderr'

    logger.setup_logger(args.verbose if 'verbose' in args else None, stream)

    Version().print(args.output_format)
