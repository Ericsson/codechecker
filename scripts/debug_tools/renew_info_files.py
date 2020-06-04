#!/usr/bin/env python3
# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

"""
This script converts old-format 'compiler_[info/includes/target].json'
files (containing unparsed, unfiltered output strings of verbose compiler
invocations) to a new-format 'compiler_info.json' file.

Its only argument is a REPORT DIR that contains either
 (a) an old-format 'compiler_info.json' file, OR
 (b) an even older pair of 'compiler_[includes/target].json' files.

Detection of these files happens automatically.

If the --clean option is not given, old files are preserved, meaning that
the old info file is backed up as 'compiler_info_old.json' (a), OR old
includes/target files are simply not removed (b).
"""

import argparse
import json
import logging
import os
import sys

LOG = logging.getLogger(__name__)

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] - %(message)s')
handler.setFormatter(formatter)

LOG.setLevel(logging.INFO)
LOG.addHandler(handler)


def new_version_detected(info):
    """
    Check whether the contents of 'compiler_info.json' are of old format
    ('target' and 'includes' values are the full output of verbose compiler
    invocations, without any parsing or filtering).
    Parameters:
        info    : Contents of info file (dictionary).
    """
    for compiler in info:
        if "Using built-in specs" in info[compiler]['target']:
            LOG.info("Old-version info file detected.")
            return False
        return True


def filter_includes(include_dirs):
    """
    Filter the list of compiler includes.
    We want to elide GCC's include-fixed and intrinsic directory.
    See docs/gcc_incompatibilities.md.
    """
    def contains_intrinsic_headers(include_dir):
        """
        Return True if the given directory contains at least one
        intrinsic header.
        """
        if not os.path.exists(include_dir):
            return False
        for include_file in os.listdir(include_dir):
            if include_file.endswith("intrin.h"):
                return True
        return False

    result = []
    for include_dir in include_dirs:
        if os.path.basename(
                os.path.normpath(include_dir)) == "include-fixed":
            continue
        if contains_intrinsic_headers(include_dir):
            continue
        result.append(include_dir)
    return result


def process_includes(includes_str):
    """
    Extract compiler include paths from a string of verbose compiler
    invocation output.
    """
    start_mark = "#include <...> search starts here:"
    end_mark = "End of search list."

    include_paths = []
    do_append = False
    for line in includes_str.splitlines():
        if line.startswith(end_mark):
            break
        if do_append:
            line = line.strip()
            fpos = line.find("(framework directory)")
            if fpos == -1:
                include_paths.append(line)
            else:
                include_paths.append(line[:fpos - 1])

        if line.startswith(start_mark):
            do_append = True

    return filter_includes(include_paths)


def process_target(target_str):
    """
    Extract target architecture from a string of verbose compiler
    invocation output.
    """
    target_label = "Target:"
    target_clean = ""

    for line in target_str.splitlines(True):
        line = line.strip().split()
        if len(line) > 1 and line[0] == target_label:
            target_clean = line[1]

    return target_clean


def create_compiler_info_json(old_info, filepath):
    """
    Convert information from old 'compiler_info.json' or even older
    'compiler_[includes/target].json' files into a new-format
    'compiler_info.json' file that can be used with new CodeChecker versions.
    Parameters:
        old_info : Dictionary containing the following data for each compiler:
                   (a) unparsed, unfiltered include paths (string),
                   (b) unparsed target (string),
                   (c) default compiler standard (string).
        filepath : Path to 'compiler_info.json' file that should be created.
    """
    info = dict()

    for compiler in old_info:
        include_paths = process_includes(old_info[compiler]['includes'])
        for idx, _ in enumerate(include_paths):
            include_paths[idx] = "-isystem %s" % include_paths[idx]
        compiler_data = {
            "includes": include_paths,
            "target": process_target(old_info[compiler]['target']),
            "default_standard": old_info[compiler]['default_standard']}

        # There was no language information in the previous
        # compiler_info.json files. To be compatible with the new format
        # are duplicating the information for both languages.
        # It is possible that the wrong include path will be set
        # for the wrong language (C includes for C++) but at least one of them
        # will be right. We can not do better here because the
        # original compiler might not be available in the current environment.
        info[compiler]["c"] = compiler_data
        info[compiler]["c++"] = compiler_data

    with open(filepath, 'w', encoding='utf-8', errors="ignore") as dest:
        json.dump(info, dest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Convert old compiler info or even older compiler "
                        "target and includes files into one info file that "
                        "can be used with new CodeChecker versions.")
    parser.add_argument('dir', metavar='DIR', help='Path to directory where '
                        'the old-version "compiler_info.json" or the pair of '
                        '"compiler_[includes/target].json" files are located.')
    parser.add_argument('--clean', action='store_true', required=False,
                        default=False, help='remove old '
                        '"compiler_[includes/target/info].json" files')
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        LOG.error("%s is not a directory" % args.dir)
        sys.exit(1)

    target_file = os.path.join(args.dir, 'compiler_target.json')
    info_file = os.path.join(args.dir, 'compiler_info.json')

    if not os.path.isfile(info_file) and not os.path.isfile(target_file):
        LOG.error("Neither an old-version 'compiler_info.json' nor a "
                  "'compiler_target.json' could be found in '%s'." % args.dir)
        sys.exit(2)

    if os.path.isfile(info_file):
        # We have found a 'compiler_info.json' file.

        if os.stat(info_file).st_size == 0:
            LOG.error("'compiler_info.json' is empty.")
            sys.exit(3)

        with open(info_file, 'r', encoding='utf-8', errors="ignore") as src:
            info = json.loads(src.read())

        if new_version_detected(info):
            # If the info file is not an old-version one, we are not sure
            # what to do with it. Notify the user and exit.
            LOG.error("'compiler_info.json' already exists!")
            sys.exit(4)

        if not args.clean:
            # Rename the old JSON, otherwise we will overwrite it.
            os.rename(info_file,
                      os.path.join(args.dir, 'compiler_info_old.json'))
            LOG.info("Old 'compiler_info.json' file renamed to "
                     "'compiler_info_old.json'")

        create_compiler_info_json(info, info_file)

        LOG.info("New 'compiler_info.json' file created.")
        sys.exit(0)

    if os.path.isfile(target_file):
        # We have found a 'compiler_target.json' file.
        includes_file = os.path.join(args.dir, 'compiler_includes.json')

        if not os.path.isfile(includes_file):
            # There is no 'compiler_includes.json' to match the target file.
            LOG.error("'compiler_includes.json' not found in %s" % args.dir)
            sys.exit(5)

        LOG.info("'compiler_[includes/target].json' files detected.")

        with open(includes_file, 'r',
                  encoding='utf-8', errors="ignore") as src:
            includes = json.loads(src.read())

        with open(target_file, 'r', encoding='utf-8', errors="ignore") as src:
            target = json.loads(src.read())

        # Unify information from the two files.
        old_info = dict()
        for compiler in includes:
            old_info[compiler] = {"includes": includes[compiler],
                                  "target": target[compiler],
                                  "default_standard": ""}

        create_compiler_info_json(old_info, info_file)

        if args.clean:
            os.remove(includes_file)
            os.remove(target_file)
            LOG.info("Old 'compiler_[includes/target].json' files removed.")

        LOG.info("New 'compiler_info.json' file created.")
