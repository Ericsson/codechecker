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
import json
import os
import re
import subprocess
import sys
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
application of these automatic fixes.

Besides the provided filter options you can pipe the JSON format output of
"CodeChecker cmd diff" command to apply automatic fixes only for new reports:
CodeChecker cmd diff -b dir1 -n dir2 -o json --new | CodeChecker fixit dir2""",
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
    parser.add_argument('-i', '--interactive',
                        action='store_true',
                        default=False,
                        help="Interactive selection of fixits to apply. Fixit "
                             "items are enumerated one by one and you may "
                             "choose which ones are to be applied.")
    parser.add_argument('--checker-name',
                        nargs='*',
                        default=[],
                        help='Filter results by checker names. The checker '
                             'name can contain multiple * quantifiers which '
                             'matches any number of characters (zero or '
                             'more). So for example "*DeadStores" will '
                             'match "deadcode.DeadStores".')
    parser.add_argument('--file',
                        metavar='FILE_PATH',
                        nargs='*',
                        default=[],
                        help='Filter results by file path. The file path can '
                             'contain multiple * quantifiers which matches '
                             'any number of characters (zero or more). So if '
                             'you have /a/x.cpp and /a/y.cpp then "/a/*.cpp" '
                             'selects both.')

    logger.add_verbose_arguments(parser)
    parser.set_defaults(func=main)


def get_location_by_offset(filename, offset):
    """
    This function returns the line and column number in the given file which
    is located at the given offset.
    """
    with open(filename, encoding='utf-8', errors='ignore') as f:
        for row, line in enumerate(f, 1):
            length = len(line)
            if length < offset:
                offset -= length
            else:
                return row, offset + 1


def clang_tidy_fixit_filter(content, checker_names, file_paths, interactive,
                            reports):
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
    reports -- A list of CodeChecker reports. This can come from
               "CodeChecker cmd [diff|results] ..." command in JSON format.
    interactive -- Interactive filtering. If True then user will be asked about
                   each fixit one by one.
    """
    def make_regex(parts):
        if not parts:
            return re.compile('.*')
        parts = map(lambda part: re.escape(part).replace(r'\*', '.*'), parts)
        return re.compile('|'.join(parts) + '$')

    def ask_user(item):
        print(yaml.dump(item))
        prompt = "y/<Enter> - Yes\nOther     - No\nCtrl-C    - Cancel\nApply: "
        return input(prompt) in "Yy"

    if reports:
        def match_reports(diag_msg):
            row, col = get_location_by_offset(diag_msg['FilePath'],
                                              int(diag_msg['FileOffset']))
            return any(row == report['line'] and col == report['column'] and
                       diag_msg['FilePath'] == report['checkedFile']
                       for report in reports)
    else:
        match_reports = bool

    checker_names = make_regex(checker_names)
    file_paths = make_regex(file_paths)

    items = filter(
        lambda diag: checker_names.match(diag['DiagnosticName']) and
        len(diag['DiagnosticMessage']['Replacements']) != 0 and
        file_paths.match(diag['DiagnosticMessage']['FilePath']) and
        match_reports(diag['DiagnosticMessage']),
        content['Diagnostics'])

    if interactive:
        items = filter(ask_user, items)

    content['Diagnostics'] = list(items)


def list_fixits(inputs, checker_names, file_paths, interactive, reports):
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
                clang_tidy_fixit_filter(content, checker_names, file_paths,
                                        interactive, reports)
            print(yaml.dump(content))


def apply_fixits(inputs, checker_names, file_paths, interactive, reports):
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
                    clang_tidy_fixit_filter(content, checker_names, file_paths,
                                            interactive, reports)

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

    try:
        reports = None if sys.stdin.isatty() else json.loads(sys.stdin.read())
    except json.decoder.JSONDecodeError as ex:
        LOG.error("JSON format error on standard input: %s", ex)
        sys.exit(1)

    if 'list' in args:
        list_fixits(args.input, args.checker_name, args.file,
                    args.interactive, reports)
    else:
        apply_fixits(args.input, args.checker_name, args.file,
                     args.interactive, reports)
