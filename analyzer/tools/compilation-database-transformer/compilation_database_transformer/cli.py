#!/usr/bin/env python3
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
"""
Manipulate, preprocess and transform compilation database JSON files.
Provides pretty printing, compilation result checking and adjusting
compilation parameters features.ccdb-tool is used to manipulate
compile command databases.
"""

import argparse
import operator
import shlex
import subprocess
import sys

from compilation_database_transformer.build_action import BuildAction
from compilation_database_transformer.log_parser import parse_unique_log
from compilation_database_transformer.pipeline import JsonPipeline


def handle_print(args):
    """
    Pretty print the input json.
    """

    JsonPipeline(args.output) \
        .flatten() \
        .feed(args.input)


def handle_clangify(args):
    """
    Make every entry in every compilation database clang-compatible.
    """

    JsonPipeline(args.output) \
        .append_map(lambda x: parse_unique_log(x, './')) \
        .append_map(operator.itemgetter(0)) \
        .flatten() \
        .append_map(BuildAction.to_analyzer_dict) \
        .feed(args.input)


def swap_comp_to_clang(entry):
    command = entry['command']
    new_cmd = shlex.split(command)
    new_cmd[0] = 'clang++' if '++' in new_cmd[0] else 'clang'
    new_cmd = ' '.join(new_cmd)
    return {
        'file': entry['file'],
        'command': new_cmd,
        'directory': entry['directory']
    }


def check_command_validity(entry):
    try:
        proc = subprocess.Popen(
            entry['command'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        outs, errs = proc.communicate()
        error_code = proc.returncode

        if error_code == 0:
            status = 'OK'
            message = outs
        else:
            status = 'FAIL'
            message = errs
    except Exception as e:
        status = 'EXCEPTION'
        message = str(e)

    return {
        'file': entry['file'],
        'status': status,
        'message': message
    }


def handle_check(args):
    """
    Swap compiler binary to clang or clang++, and execute the compilation.
    """

    JsonPipeline(args.output) \
        .flatten() \
        .append_map(swap_comp_to_clang) \
        .append_map(check_command_validity) \
        .feed(args.input)


def main():
    argparser = argparse.ArgumentParser(prog='ccdb-tool')
    argparser.add_argument(
        'command',
        nargs='?',
        choices=['print', 'clangify', 'check'],
        default='print')

    argparser.add_argument(
        '--input',
        nargs='*',
        type=argparse.FileType('r'),
        default=[sys.stdin])

    argparser.add_argument(
        '--output',
        nargs='?',
        type=argparse.FileType('w'),
        default=sys.stdout)

    args = argparser.parse_args()

    if args.command == 'print':
        handle_print(args)
    elif args.command == 'clangify':
        handle_clangify(args)
    else:
        handle_check(args)


if __name__ == '__main__':
    main()
