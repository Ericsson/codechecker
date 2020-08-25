#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------


import argparse
import json
import os
import platform
import subprocess

import prepare_compile_cmd
import prepare_compiler_info
import prepare_analyzer_cmd


def execute(cmd):
    print("Executing command: " + ' '.join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="ignore")
        out, err = proc.communicate()

        print("stdout:\n\n" + out)
        print("stderr:\n\n" + err)

        if proc.returncode != 0:
            print('Unsuccessful run: "' + ' '.join(cmd) + '"')
            raise Exception("Unsuccessful run of command.")
        return out
    except OSError:
        print('Failed to run: "' + ' '.join(cmd) + '"')
        raise


def get_triple_arch(analyze_command_file):
    with open(analyze_command_file,
              encoding="utf-8", errors="ignore") as f:
        cmd = f.readline()

    cmd = cmd.split()
    for flag in cmd:
        if flag.startswith('--target='):
            return flag[9:].split('-')[0]  # 9 == len('--target=')

    return platform.machine()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prepare all commands '
        'to execute in local environmennt for debugging.')
    parser.add_argument(
        '--sources_root',
        default='./sources-root',
        help="Path of the source root.")
    parser.add_argument(
        '--report_dir',
        default='..',
        help="Path of the report dir.")
    parser.add_argument(
        '--clang',
        required=True,
        help="Path to the clang binary.")
    parser.add_argument(
        '--clang_plugin_name', default=None,
        help="Name of the used clang plugin.")
    parser.add_argument(
        '--clang_plugin_path', default=None,
        help="Path to the used clang plugin.")
    args = parser.parse_args()

    compile_cmd_debug = "compile_cmd_DEBUG.json"
    with open(compile_cmd_debug, 'w',
              encoding="utf-8", errors="ignore") as f:
        f.write(
            json.dumps(
                prepare_compile_cmd.prepare(
                    os.path.join(args.report_dir, "compile_cmd.json"),
                    args.sources_root),
                indent=4))

    compiler_info_debug = "compiler_info_DEBUG.json"
    with open(compiler_info_debug, 'w',
              encoding="utf-8", errors="ignore") as f:
        f.write(
            json.dumps(
                prepare_compiler_info.prepare(
                    os.path.join(args.report_dir, "compiler_info.json"),
                    args.sources_root),
                indent=4))

    # ctu-collect
    out = execute(["CodeChecker", "analyze", "--ctu-collect",
                   compile_cmd_debug,
                   "--compiler-info-file", compiler_info_debug,
                   "-o", "report_debug",
                   "--verbose", "debug"])

    analyzer_command_debug = "analyzer-command_DEBUG"
    target = get_triple_arch('./analyzer-command')
    with open(analyzer_command_debug, 'w',
              encoding="utf-8", errors="ignore") as f:
        f.write(
            prepare_analyzer_cmd.prepare(
                "./analyzer-command",
                prepare_analyzer_cmd.PathOptions(
                    args.sources_root,
                    args.clang,
                    args.clang_plugin_name,
                    args.clang_plugin_path,
                    "./report_debug/ctu-dir/" + target)))

    print(
        "Preparation of files for debugging is done. "
        "Now you can execute the generated analyzer command. "
        "E.g. $ bash % s" %
        analyzer_command_debug)
