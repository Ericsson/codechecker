# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Defines the CodeChecker action for applying fixits.
"""

import argparse
import os
import re
import subprocess
import tempfile
import yaml

from codechecker_analyzer import analyzer_context
from codechecker_common import arg, logger

LOG = logger.get_logger('system')


def get_argparser_ctor_args():
    """
    This method returns a dict containing the kwargs for constructing an
    argparse.ArgumentParser (either directly or as a subparser).
    """

    return {
        'prog': 'CodeChecker fixit',
        'formatter_class': arg.RawDescriptionDefaultHelpFormatter,
        'description': """
Some analyzers may suggest some automatic bugfixes. Most of the times these are
style issues which can be fixed easily. This command handles the listing and
application of these automatic fixes.""",
        'help': "Apply automatic fixes based on the suggestions of the "
                "analyzers"
    }


def add_arguments_to_parser(parser):
    """
    Add the subcommand's arguments to the given argparse.ArgumentParser.
    """

    parser.add_argument('input',
                        type=str,
                        nargs='+',
                        metavar='folder',
                        help="The analysis result folder(s) containing "
                             "analysis results and fixits which should be "
                             "applied.")
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=argparse.SUPPRESS,
                        help="List the available automatic fixes.")
    parser.add_argument('--checker-name',
                        nargs='*',
                        help='Filter results by checker names. The checker '
                             'name can contain multiple * quantifiers which '
                             'matches any number of characters (zero or '
                             'more). So for example "*DeadStores" will '
                             'match "deadcode.DeadStores".')
    parser.add_argument('--file',
                        metavar='FILE_PATH',
                        nargs='*',
                        help='Filter results by file path. The file path can '
                             'contain multiple * quantifiers which matches '
                             'any number of characters (zero or more). So if '
                             'you have /a/x.cpp and /a/y.cpp then "/a/*.cpp" '
                             'selects both.')

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def clang_tidy_fixit_filter(content, checker_names, file_paths):
    """
    This function filters the content of a replacement .yaml file.
    content -- The content of a replacement .yaml file parsed to an object by
               yaml module.
    checker_names -- A list of checker names possibly containing * joker
                     characters. The full checker name must match in order to
                     apply it.
    file_paths -- A list of file paths to which the fixits will be applied.
                  A file path may possibly contain * joker characters. The
                  full path must match in order to apply it.
    """
    def make_regex(parts):
        if not parts:
            return re.compile('.*')
        parts = map(lambda part: re.escape(part).replace(r'\*', '.*'), parts)
        return re.compile('|'.join(parts) + '$')

    checker_names = make_regex(checker_names)
    file_paths = make_regex(file_paths)

    content['Diagnostics'] = list(filter(
        lambda diag: checker_names.match(diag['DiagnosticName']) and
        len(diag['DiagnosticMessage']['Replacements']) != 0 and
        file_paths.match(diag['DiagnosticMessage']['FilePath']),
        content['Diagnostics']))


def list_fixits(inputs, checker_names, file_paths):
    """
    This function dumps the .yaml files to the standard output like a "dry run"
    with the replacements. See clang_tidy_fixit_filter() for the documentation
    of the filter options.
    inputs -- A list of report directories which contains the fixit dumps in a
              subdirectory named "fixit".
    """
    for i in inputs:
        fixit_dir = os.path.join(i, 'fixit')

        if not os.path.isdir(fixit_dir):
            continue

        for fixit_file in os.listdir(fixit_dir):
            with open(os.path.join(fixit_dir, fixit_file),
                      encoding='utf-8', errors='ignore') as f:
                content = yaml.load(f, Loader=yaml.BaseLoader)
                clang_tidy_fixit_filter(content, checker_names, file_paths)
            print(yaml.dump(content))


def apply_fixits(inputs, checker_names, file_paths):
    """
    This function applies the replacements from the .yaml files.
    inputs -- A list of report directories which contains the fixit dumps in a
              subdirectory named "fixit".
    """
    for i in inputs:
        fixit_dir = os.path.join(i, 'fixit')

        if not os.path.isdir(fixit_dir):
            continue

        with tempfile.TemporaryDirectory() as out_dir:
            for fixit_file in os.listdir(fixit_dir):
                with open(os.path.join(fixit_dir, fixit_file),
                          encoding='utf-8', errors='ignore') as f:
                    content = yaml.load(f, Loader=yaml.BaseLoader)
                    clang_tidy_fixit_filter(content, checker_names, file_paths)

                if len(content['Diagnostics']) != 0:
                    with open(os.path.join(out_dir, fixit_file), 'w',
                              encoding='utf-8', errors='ignore') as out:
                        yaml.dump(content, out)

            proc = subprocess.Popen([
                analyzer_context.get_context().replacer_binary,
                out_dir])
            proc.communicate()


def main(args):
    """
    Entry point for the command handling automatic fixes.

    TODO: Currently clang-tidy is the only tool which supports the dumping of
    fixit replacements. In this script we assume that the replacement dump
    .yaml files are in the format so clang-apply-replacement Clang tool can
    consume them.
    """

    logger.setup_logger(args.verbose if 'verbose' in args else None)

    context = analyzer_context.get_context()

    if not context.replacer_binary:
        LOG.error("clang-apply-replacements tool is not found")
        return

    if 'list' in args:
        list_fixits(args.input, args.checker_name, args.file)
    else:
        apply_fixits(args.input, args.checker_name, args.file)
