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
import shutil
import subprocess

import prepare_compile_cmd
import prepare_compiler_info
import prepare_analyzer_cmd


def execute(cmd, env):
    print("Executing command: " + ' '.join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            env=env,
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
        default='.',
        help="Path of the report dir.")
    parser.add_argument(
        '--clang',
        required=True,
        help="Path to the clang binary.")
    args = parser.parse_args()

    # CodeChecker log outputs 'compile_cmd.json' by default.
    # Let's canonicalize the name as 'compilation_database.json' instead.
    try:
        shutil.move("compile_cmd.json", "compilation_database.json")
        print("renamed 'compile_cmd.json' to 'compilation_database.json'")
    except FileNotFoundError:
        pass

    compile_cmd_debug = "compilation_database_DEBUG.json"
    with open(compile_cmd_debug, 'w',
              encoding="utf-8", errors="ignore") as f:
        f.write(
            json.dumps(
                prepare_compile_cmd.prepare(
                    os.path.join(args.report_dir, "compilation_database.json"),
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

    # ctu-collect, using the provided clang
    env = os.environ
    env['PATH'] = f"{os.path.dirname(args.clang)}:{env['PATH']}"
    env['CC_ANALYZERS_FROM_PATH'] = 'yes'
    out = execute(["CodeChecker", "analyze", "--ctu-collect",
                   compile_cmd_debug,
                   "--compiler-info-file", compiler_info_debug,
                   "-o", "report_debug",
                   "--verbose", "debug"], env)

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
                    "./report_debug/ctu-dir/" + target)))

    print(
        "Preparation of files for debugging is done. "
        "Now you can execute the generated analyzer command. "
        "E.g. $ bash %s" %
        analyzer_command_debug)
