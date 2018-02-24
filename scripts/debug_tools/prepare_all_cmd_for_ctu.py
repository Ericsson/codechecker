#!/usr/bin/env python
# -------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -------------------------------------------------------------------------
import argparse
import json
import os
import platform
import subprocess

import prepare_compile_cmd
import prepare_compiler_includes
import prepare_compiler_target
import prepare_analyzer_cmd


def execute(cmd, verbose = True):
    if verbose:
        print("Executing command: " + ' '.join(cmd))
    try:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if verbose:
            print("stdout:\n\n" + out.decode("utf-8"))
            print("stderr:\n\n" + err.decode("utf-8"))

        if proc.returncode != 0:
            if verbose:
                print('Unsuccessful run: "' + ' '.join(cmd) + '"')
            raise Exception("Unsuccessful run of command.")
        return out
    except OSError:
        print('Failed to run: "' + ' '.join(cmd) + '"')
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
    def __init__(
            self,
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


def prepare(pathOptions):
    compile_cmd_debug = "compile_cmd_DEBUG.json"
    with open(compile_cmd_debug, 'w') as f:
        f.write(
            json.dumps(
                prepare_compile_cmd.prepare(
                    os.path.join(pathOptions.report_dir, "compile_cmd.json"),
                    pathOptions.sources_root),
                indent=4))

    compiler_includes_debug = "compiler_includes_DEBUG.json"
    with open(compiler_includes_debug, 'w') as f:
        f.write(
            json.dumps(
                prepare_compiler_includes.prepare(
                    os.path.join(pathOptions.report_dir, "compiler_includes.json"),
                    pathOptions.sources_root),
                indent=4))

    compiler_target_debug = "compiler_target_DEBUG.json"
    with open(compiler_target_debug, 'wb') as f:
        f.write(
            json.dumps(
                prepare_compiler_target.prepare(
                    os.path.join(pathOptions.report_dir, "compiler_target.json"),
                    pathOptions.sources_root),
                indent=4))

    # ctu-collect
    out = execute(["CodeChecker", "analyze", "--ctu-collect",
                   compile_cmd_debug,
                   "--compiler-includes-file", compiler_includes_debug,
                   "--compiler-target-file", compiler_target_debug,
                   "-o", "report_debug",
                   "--verbose", "debug"])

    analyzer_command_debug = "analyzer-command_DEBUG"
    target = get_triple_arch('./analyzer-command')
    with open(analyzer_command_debug, 'w') as f:
        f.write(
            prepare_analyzer_cmd.prepare(
                "./analyzer-command",
                prepare_analyzer_cmd.PathOptions(
                    pathOptions.sources_root,
                    pathOptions.clang,
                    pathOptions.clang_plugin_name,
                    pathOptions.clang_plugin_path,
                    os.path.abspath("./report_debug/ctu-dir") + "/" + target)))

    print(
        "Preparation of files for debugging is done. "
        "Now you can execute the generated analyzer command. "
        "E.g. $ bash % s" %
        analyzer_command_debug)


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
    # change the paths to absolute
    args.sources_root = os.path.abspath(args.sources_root)
    prepare(PathOptions(
            args.sources_root,
            args.clang,
            args.clang_plugin_name,
            args.clang_plugin_path,
            args.report_dir))


