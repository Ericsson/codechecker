# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Utilities for compilation database handling.
"""


import os
import shlex
from typing import Callable, Dict, List, Optional

from codechecker_common.util import load_json


# For details see
# https://gcc.gnu.org/onlinedocs/gcc-12.2.0/gcc/Overall-Options.html#Overall-Options
C_CPP_OBJC_OBJCPP_EXTS = [
    '.c', '.i', '.ii', '.m', '.mi', '.mm', '.M', '.mii',
    '.cc', '.cp', '.cxx', '.cpp', '.CPP', 'c++', '.C',
    '.hh', '.H', '.hp', '.hxx', '.hpp', '.HPP', '.h++', '.tcc'
]


# Compilation database is conventionally stored in this file. Many Clang-based
# tools rely on this file name, and CMake exports this too.
COMPILATION_DATABASE = "compile_commands.json"


def find_closest_compilation_database(path: str) -> Optional[str]:
    """
    Traverse the parent directories of the given path and find the closest
    compile_commands.json. If no JSON file exists with this name up to the root
    then None returns.
    The path of the first compilation database is returned even if it doesn't
    contain a corresponding entry for the given source file in "path".
    """
    path = os.path.abspath(path)
    root = os.path.abspath(os.sep)

    while True:
        path = os.path.dirname(path)
        compile_commands_json = os.path.join(path, COMPILATION_DATABASE)

        if os.path.isfile(compile_commands_json):
            return compile_commands_json

        if path == root:
            break


def change_args_to_command_in_comp_db(compile_commands: List[Dict]):
    """
    In CodeChecker we support compilation databases where the JSON object of a
    build action contains "file", "directory" and "command" fields. However,
    compilation databases from intercept build contain "arguments" instead of
    "command" which is a list of command-line arguments instead of the same
    command as a single string. This function make this appropriate conversion.
    """
    for cc in compile_commands:
        if 'command' not in cc:
            # TODO: shlex.join(cmd) would be more elegant after upgrading to
            # Python 3.8.
            cc['command'] = ' '.join(map(shlex.quote, cc['arguments']))
            del cc['arguments']


def find_all_compilation_databases(path: str) -> List[str]:
    """
    Collect all compilation database paths that may be relevant for the source
    files at the given path. This means compilation databases anywhere under
    this path and in the parent directories up to the root.
    """
    dirs = []

    for root, _, files in os.walk(path):
        if COMPILATION_DATABASE in files:
            dirs.append(os.path.join(root, COMPILATION_DATABASE))

    path = os.path.abspath(path)
    root = os.path.abspath(os.sep)

    while True:
        path = os.path.dirname(path)
        compile_commands_json = os.path.join(path, COMPILATION_DATABASE)

        if os.path.isfile(compile_commands_json):
            dirs.append(compile_commands_json)

        if path == root:
            break

    return dirs


def build_action_describes_file(file_path: str) -> Callable[[Dict], bool]:
    """
    Returns a function which checks whether a build action belongs to the
    given file_path. This returned function can be used for filtering
    build actions in a compilation database to find build actions belonging
    to the given source file.
    """
    def describes_file(build_action) -> bool:
        return os.path.abspath(file_path) == os.path.abspath(
            os.path.join(build_action['directory'], build_action['file']))
    return describes_file


def is_c_lang_source_file(source_file_path: str) -> bool:
    """
    A file is candidate if a build action may belong to it in some
    compilation database, i.e. it is a C/C++/Obj-C source file.
    """
    return os.path.isfile(source_file_path) and \
        os.path.splitext(source_file_path)[1] in C_CPP_OBJC_OBJCPP_EXTS


def find_build_actions_for_file(file_path: str) -> List[Dict]:
    """
    Find the corresponding compilation database belonging to the given
    source file and return a list of build actions that describe its
    compilation.
    """
    comp_db = find_closest_compilation_database(file_path)

    if comp_db is None:
        return []

    return list(filter(
        build_action_describes_file(file_path),
        load_json(comp_db)))


def gather_compilation_database(analysis_input: str) -> Optional[List[Dict]]:
    """
    Return a compilation database that describes the build of the given
    analysis_input:

    - If analysis_input is a compilation database JSON file then its entries
      return.
    - If analysis_input is a C/C++/Obj-C source file then the corresponding
      build command is found from the compilation database. Only the innermost
      compilation database is checked (see find_closest_compilation_database()
      for details).
    - If analysis_input is a directory then a compilation database with the
      build commands of all C/C++/Obj-C files in it return.

    If none of these apply (e.g. analysis_input is a Python source file which
    doesn't have a compilation database) then None returns.
    """
    def __select_compilation_database(
        comp_db_paths: List[str],
        source_file: str
    ) -> Optional[str]:
        """
        Helper function for selecting the corresponding compilation database
        for the given source file, i.e. the compilation database in the closest
        parent directory, even if it doesn't contain a build action belonging
        to this file.
        """
        comp_db_paths = list(map(os.path.dirname, comp_db_paths))
        longest = os.path.commonpath(comp_db_paths + [source_file])
        if longest in comp_db_paths:
            return os.path.join(longest, COMPILATION_DATABASE)

    # Case 1: analysis_input is a compilation database JSON file.

    build_actions = load_json(analysis_input, display_warning=False)

    if build_actions is not None:
        pass

    # Case 2: analysis_input is a C/C++/Obj-C source file.

    elif is_c_lang_source_file(analysis_input):
        build_actions = find_build_actions_for_file(analysis_input)

    # Case 3: analysis_input is a directory.

    elif os.path.isdir(analysis_input):
        compilation_database_files = \
            find_all_compilation_databases(analysis_input)

        build_actions = []

        for comp_db_file in compilation_database_files:
            comp_db = load_json(comp_db_file)

            if not comp_db:
                continue

            for ba in comp_db:
                file_path = os.path.join(ba["directory"], ba["file"])

                if os.path.commonpath([file_path, analysis_input]) \
                        == analysis_input and __select_compilation_database(
                        compilation_database_files,
                        file_path) == comp_db_file:
                    build_actions.append(ba)

    # Compilation database transformation.
    if build_actions is not None:
        change_args_to_command_in_comp_db(build_actions)

    return build_actions
