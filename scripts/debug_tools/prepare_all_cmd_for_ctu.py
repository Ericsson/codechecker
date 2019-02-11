#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
import json
import logging
import os
import platform
import subprocess

import prepare_compile_cmd
import prepare_compiler_info
import prepare_analyzer_cmd

LOG = logging.getLogger(__name__)

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s %(asctime)s] - %(message)s',
                              '%Y-%m-%d %H:%M')
handler.setFormatter(formatter)

LOG.setLevel(logging.INFO)
LOG.addHandler(handler)


def execute(cmd, cwd=None, env=None):
    LOG.info("Executing command: %s", ' '.join(cmd))
    try:
        proc = subprocess.run(cmd,
                              cwd=cwd,
                              env=env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True)
        if proc.stdout:
            LOG.info("START OF STDOUT\n%s", proc.stdout)
            LOG.info("END OF STDOUT")
        if proc.stderr:
            LOG.info("START OF STDERR\n%s", proc.stderr)
            LOG.info("END OF STDERR")
        if proc.returncode != 0:
            LOG.error('Unsuccessful run: "%s"', ' '.join(cmd))
            raise Exception("Command run unsuccessful")
        return proc.stdout
    except OSError:
        LOG.error('Failed to run: "%s"', ' '.join(cmd))
        raise


def get_triple_arch(analyze_command_file):
    with open(analyze_command_file) as f:
        cmd = f.readline()

    cmd = cmd.split()
    for flag in cmd:
        if flag.startswith('--target='):
            return flag[9:].split('-')[0]  # 9 == len('--target=')

    return platform.machine()


class PathOptions:
    def __init__(self,
                 sources_root,
                 clang,
                 clang_plugin_name,
                 clang_plugin_path,
                 report_dir):
        self.sources_root = sources_root
        self.clang = clang
        self.clang_plugin_name = clang_plugin_name
        self.clang_plugin_path = clang_plugin_path
        self.report_dir = report_dir


def prepare(jobs, path_options, collect=True):
    compile_cmd_debug = "compile_cmd_DEBUG.json"
    with open(compile_cmd_debug, 'w') as f:
        f.write(
            json.dumps(
                prepare_compile_cmd.prepare(
                    os.path.join(path_options.report_dir, "compile_cmd.json"),
                    path_options.sources_root),
                indent=4))

    compiler_info_debug = "compiler_info_DEBUG.json"
    with open(compiler_info_debug, 'w') as f:
        f.write(
            json.dumps(
                prepare_compiler_info.prepare(
                    os.path.join(path_options.report_dir,
                                 "compiler_info.json"),
                    path_options.sources_root),
                indent=4))

    if collect:
        execute(["CodeChecker", "analyze", "--ctu-collect",
                 compile_cmd_debug,
                 "--compiler-info-file", compiler_info_debug,
                 "-o", "report-debug", "-j", str(jobs),
                 "--verbose", "debug"])

    analyzer_command_debug = "analyzer-command_DEBUG"
    target = get_triple_arch('./analyzer-command')
    ctu_dir_for_target = os.path.join(
            os.path.abspath("./report-debug/ctu-dir"), target)

    with open(analyzer_command_debug, 'w') as f:
        f.write(
            prepare_analyzer_cmd.prepare(
                "./analyzer-command",
                prepare_analyzer_cmd.PathOptions(
                    path_options.sources_root,
                    path_options.clang,
                    path_options.clang_plugin_name,
                    path_options.clang_plugin_path,
                    ctu_dir_for_target)))

    LOG.info("Preparation of files for debugging is done. "
             "Now you can execute the generated analyzer command. "
             "E.g. $ bash % s", analyzer_command_debug)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prepare all commands '
                    'to execute in local environmennt for debugging.')
    parser.add_argument(
        '--sources-root',
        default='./sources-root',
        help="Path of the source root.")
    parser.add_argument(
        '--report-dir',
        default='..',
        help="Path of the report dir.")
    parser.add_argument(
        '--clang',
        required=True,
        help="Path to the clang binary.")
    parser.add_argument(
        '--clang-plugin-name', default=None,
        help="Name of the used clang plugin.")
    parser.add_argument(
        '--clang-plugin-path', default=None,
        help="Path to the used clang plugin.")
    parser.add_argument(
        '-j', '--jobs',
        type=int, dest="jobs", required=False, default=1,
        help="Number of threads to use in ctu-collect.")
    args = parser.parse_args()

    args.sources_root = os.path.abspath(args.sources_root)
    prepare(args.jobs, PathOptions(args.sources_root,
                                   args.clang,
                                   args.clang_plugin_name,
                                   args.clang_plugin_path,
                                   args.report_dir))
