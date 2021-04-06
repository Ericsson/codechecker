#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
Run bazel aquery to produce compilation database (compile_commands.json)
for particular bazel build command
"""

from __future__ import print_function
import argparse
import json
import logging
import os
import re
import shlex
import subprocess


def parse_args():
    """
    Parse command line arguments or show help.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=__doc__)
    parser.add_argument("-o", "--output",
                        default="compile_commands.json",
                        help="output compile_commands.json file")
    parser.add_argument("-b", "--build",
                        help="bazel build command arguments")
    parser.add_argument("-v", "--verbosity",
                        default=1,
                        action="count",
                        help="enable verbose logging")
    parser.add_argument("--log-format",
                        default="[bazel] %(levelname)5s: %(message)s",
                        help=argparse.SUPPRESS)

    options = parser.parse_args()

    if options.verbosity >= 2:
        log_level = logging.DEBUG
    elif options.verbosity >= 1:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(level=log_level, format=options.log_format)

    return options


def split_to_list(arguments):
    """
    Split argument string to list
    """
    if type(arguments) is list:
        return arguments
    else:
        return shlex.split(arguments)


def run_command(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    Run shell command
    """
    cmd = split_to_list(command)
    process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
    out, err = process.communicate()
    if process.returncode:
        logging.error("Command: %s...\nError: %s", command, err)
    return out.decode("utf-8")


def bazel_aquery(build_arguments):
    """
    Run bazel query and return list of source files, e.g.:
    bazel cquery 'kind("source file", deps("@workspace//target"))'
        --config=something --noimplicit_deps --notool_deps
    """
    arguments = split_to_list(build_arguments)
    targets = []
    configs = []
    bazel = arguments[0]
    logging.debug("Bazel: %s", bazel)
    logging.debug("Bazel build arguments:")
    for argument in arguments:
        logging.debug("   %s", argument)
        if re.search(r"^(@|:|\/\/)\S*", argument) or argument == "...":
            targets.append(argument)
        elif re.search(r"^--\S*", argument):
            configs.append(argument)
    logging.debug("Targets: %s", targets)
    logging.debug("Configs: %s", configs)
    if len(targets) < 1:
        logging.error(
            "No targets found for bazel query in: %s",
            build_arguments)
        return

    deps = " + ".join([
        "deps(\"{target}\")".format(target=target) for target in targets
    ])
    logging.debug("Deps: %s", deps)

    options = [
        "--output=jsonproto",
        "--include_artifacts=false",
    ]
    function = "mnemonic(\"CppCompile\", {deps})".format(deps=deps)
    command = "{bazel} aquery {options} '{function}' {configs}".format(
        bazel=bazel,
        options=" ".join(options),
        function=function,
        configs=" ".join(configs))
    logging.debug("Command: %s", command)

    out = run_command(command)
    if out:
        data = json.loads(out)
        return data


def get_compile_commands(data,
                         directories=["."],
                         base_dir=None,
                         output_base=None):
    """
    Produce compile commands from action graph JSON data
    """
    compile_commands = []
    not_found = 0
    skipped = 0
    for action in data["actions"]:
        if "mnemonic" in action and action["mnemonic"] in ["CppCompile"]:
            arguments = action["arguments"]
            try:
                index = arguments.index("-c")
                file = arguments[index + 1]
                if not file.endswith(".asm"):
                    (full_path, directory) = find_file(file, directories)
                    if full_path and directory:
                        if base_dir:
                            directory = base_dir
                        compile_command = {
                            "file": full_path,
                            "directory": directory,
                            "command": " ".join(arguments),
                        }
                        filter_compile_command(compile_command, output_base)
                        compile_commands.append(compile_command)
                        logging.info("Add file: %s", file)
                    else:
                        logging.warning("Cannot find: %s", file)
                        not_found += 1
                else:
                    logging.info("Skipping: %s", file)
                    skipped += 1
            except ValueError:
                logging.warning("Wrong compile command: %s", str(arguments))
    logging.info("%d files added, %d skipped (asm), %d not found",
                 len(compile_commands), skipped, not_found)
    return compile_commands


def find_file(file, directories):
    """
    Find file in the list of directories.
    Return full path and corresponding directory.
    """
    for directory in directories:
        full_path = os.path.join(directory, file)
        if os.path.isfile(full_path):
            return (full_path, directory)
    return (False, False)


def filter_compile_command(compile_command, output_base):
    """
    Remove irrelevant options and change paths
    """
    command = compile_command["command"]
    if output_base:
        # bazel-out/k8-fastbuild/bin/external/ -> /abs/path/external/
        command = re.sub(r"( |=)bazel-out\/\S*\/bin\/external\/",
                         r"\1" + output_base + "/external/",
                         command)
    else:
        # bazel-out/k8-fastbuild/bin/external/ -> ../../external/
        command = re.sub(r"( |=)bazel-out\/\S*\/bin\/external\/",
                         r"\1../../external/",
                         command)
    # Remove unsupported options (clang)
    command = re.sub(r" -MD ", " ", command)
    command = re.sub(r" -MF \S* ", " ", command)
    command = re.sub(r" -MT \S* ", " ", command)
    compile_command["command"] = command


def run(build_command, output_file_name):
    """
    Run bazel aquaery and generate compile_commands.json:
    - get bazel info params
    - run bazel aquery and parse output as JSON data
    - create compile commands from JSON data:
      * take only arguments
      * add: file, directory, command
      * change to full paths
      * filter compiler options
    - save to output file (compile_commands.json)
    """
    if not build_command:
        logging.error("No bazel build command specified")
        return False

    if not output_file_name:
        logging.error("No output file is specified")
        return False

    bazel_info = split_to_list(build_command)[0] + " info "
    bazel_workspace = run_command(bazel_info + "workspace").rstrip()
    bazel_output_base = run_command(bazel_info + "output_base").rstrip()
    bazel_execution_root = run_command(bazel_info + "execution_root").rstrip()

    bazel_work_dir = bazel_execution_root.replace("/execroot/", "/external/")
    if not os.path.exists(bazel_work_dir):
        bazel_work_dir = bazel_workspace

    logging.info("Bazel workspace:     %s", bazel_workspace)
    logging.info("Bazel output base:   %s", bazel_output_base)
    logging.info("Bazel work dir:      %s", bazel_work_dir)

    logging.info("Bazel build options: %s", build_command)
    data = bazel_aquery(build_command)
    if not data:
        logging.error("Command '%s'", build_command)
        logging.error("Produces no output")
        return False

    directories = [
        bazel_output_base,
        bazel_work_dir,
    ]
    compile_commands = get_compile_commands(
        data, directories, output_base=bazel_output_base)

    logging.info("Saving to: %s", output_file_name)
    with open(output_file_name, "w") as compile_commands_file:
        json.dump(compile_commands, compile_commands_file, indent=4)
    return True


def main():
    """
    Main function
    """
    options = parse_args()
    logging.debug("Options: %s", options)
    if not run(options.build, options.output):
        exit(1)


if __name__ == "__main__":
    main()
