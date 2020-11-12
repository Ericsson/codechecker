#!/usr/bin/env python3
"""
Copy CodeChecker entry point sub-commands.
"""
import argparse
import glob
import json
import logging
import os
import shutil

LOG = logging.getLogger('EntryPoints')

msg_formatter = logging.Formatter('[%(levelname)s] - %(message)s')
log_handler = logging.StreamHandler()
log_handler.setFormatter(msg_formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(log_handler)


def collect_subcmd(cmd_dirs, build_dir):
    '''
    This function collects all CodeChecker subcommands (like analyze, check,
    store, etc.) from "cmd_dirs" and writes them to .../cc_bin/commands.json
    file so the top-level CodeChecker script knows what subcommands are
    allowed. We assume that all python files under "cmd_dirs" belong to a
    specific subcommand.

    cmd_dirs -- List of directories where the code of subcommands can be found.
    build_dir -- CodeChecker build directory where the resulting .json file
                 is written.
    '''
    subcmds = {}

    for cmd_dir in cmd_dirs:
        for cmd_file in glob.glob(os.path.join(cmd_dir, '*')):
            cmd_file_name = os.path.basename(cmd_file)
            # Exclude files like __init__.py or __pycache__.
            if '__' not in cmd_file_name:
                # [:-3] removes '.py' extension.
                subcmds[cmd_file_name[:-3].replace('_', '-')] = \
                    os.path.join(*cmd_file.split(os.sep)[-3:])
                # In case of an absolute path only the last 3 parts are needed:
                # codechecker_<module>/cmd/<cmd_name>.py

    commands_json = os.path.join(
        build_dir, 'CodeChecker', 'cc_bin', 'commands.json')

    with open(commands_json, 'w',
              encoding="utf-8", errors="ignore") as commands:
        json.dump(subcmds, commands, sort_keys=True, indent=2)


def copy_files(files, target_dir):
    '''Copy all files of "files" to "target_dir".'''
    for f in files:
        shutil.copy2(f, target_dir)


if __name__ == "__main__":
    description = '''CodeChecker copy entry point sub-commands'''

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=description)

    parser.add_argument('--bin-file',
                        nargs='*',
                        help="List of files to be copied to 'bin' directory. "
                             "These are exported to users, so these are "
                             "directly executable.")

    parser.add_argument('--cc-bin-file',
                        nargs='*',
                        help="List of files to be copied to 'cc_bin' "
                             "directory. These are not exported to users, so "
                             "these are not directly executable.")

    parser.add_argument('--cmd-dir',
                        nargs='*',
                        help="List of directories which contain CodeChecker "
                             "sub-commands.")

    parser.add_argument('-b', '--build-dir',
                        required=True,
                        action='store',
                        dest='build_dir',
                        help="Build directory of the source repository.")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        dest='verbose',
                        help="Set verbosity level.")

    args = vars(parser.parse_args())

    if 'verbose' in args and args['verbose']:
        LOG.setLevel(logging.DEBUG)

    if args['cmd_dir']:
        collect_subcmd(args['cmd_dir'], args['build_dir'])

    if args['bin_file']:
        copy_files(
            args['bin_file'],
            os.path.join(args['build_dir'], 'CodeChecker', 'bin'))

    if args['cc_bin_file']:
        copy_files(
            args['cc_bin_file'],
            os.path.join(args['build_dir'], 'CodeChecker', 'cc_bin'))
